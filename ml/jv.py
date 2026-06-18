from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import pipeline
from keybert import KeyBERT
import joblib
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
import torch
import re

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="Main Part of Sentiment Analysis", version="18.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

device = 0 if torch.cuda.is_available() else -1
# Use float16 precision if a CUDA-enabled GPU is available to improve inference performance
dtype = torch.float16 if torch.cuda.is_available() else torch.float32

logger.info("Loading High-Accuracy DeBERTa Models...")
zero_shot_pipeline = pipeline("zero-shot-classification", model="MoritzLaurer/deberta-v3-base-zeroshot-v2.0", device=device, torch_dtype=dtype, truncation=True, max_length=512)
sarcasm_detector = pipeline("text-classification", model="cardiffnlp/twitter-roberta-base-irony", device=device, torch_dtype=dtype, truncation=True, max_length=512)
kw_model = KeyBERT()

try:
    spam_classifier = joblib.load("spam_classifier_v3.pkl")
except FileNotFoundError:
    spam_classifier = None
    logger.warning("spam_classifier_v3.pkl not found.")

class Post(BaseModel):
    content: str
    target_brand: str
    product: str
    features: list[str]

def get_content_safety(text: str) -> str:
    if spam_classifier:
        prediction = spam_classifier.predict([text])[0]
        if prediction == 1: return "PROMO/SPAM"
        elif prediction == 2: return "ADULT/NSFW"
    return "SAFE"

def extract_relevant_context(text: str, keywords: list, window: int = 1):
    """Isolates the sentences mentioning the product to prevent long text from diluting the sentiment."""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    if len(sentences) <= 2: return text 
        
    relevant_indices = set()
    keyword_list = [k.lower() for k in keywords]
    
    for i, sent in enumerate(sentences):
        if any(kw in sent.lower() for kw in keyword_list):
            for w in range(max(0, i - window), min(len(sentences), i + window + 1)):
                relevant_indices.add(w)
                
    if not relevant_indices: return text 
    return " ".join([sentences[i] for i in sorted(relevant_indices)])

def analyze_decoupled_nlp(full_text: str, target_brand: str, product: str, features: list):
    sarcasm_check = sarcasm_detector(full_text)[0]
    is_sarcastic = sarcasm_check['label'].lower() in ['irony', 'sarcasm', 'label_1']

    # 1. INTENT DETECTION
    # Map raw text to one of seven conversational intent classes using zero-shot classification
    intent_labels = [
        "asking a question or seeking help",
        "asking for recommendations or buying advice",
        "reporting a bug, failure, or expressing frustration",
        "comparing two different brands or products",
        "praising a product or sharing a positive review",
        "selling a product, classified ad, or promotional",
        "sharing news, sharing links, or neutral discussion"
    ]
    res_intent = zero_shot_pipeline(full_text, candidate_labels=intent_labels)
    top_intent = res_intent['labels'][0]

    # Convert classification labels to normalized uppercase intent categories
    if "question" in top_intent: intent = "QUESTION"
    elif "recommendations" in top_intent: intent = "REQUEST"
    elif "bug" in top_intent: intent = "COMPLAINT"
    elif "comparing" in top_intent: intent = "COMPARISON"
    elif "praising" in top_intent: intent = "PRAISE"
    elif "selling" in top_intent: intent = "SALE"
    else: intent = "DISCUSSION"

    # Strip the noise so the model focuses ONLY on your product
    # Extract only the surrounding context containing product/brand keywords
    search_keywords = [target_brand, product] + features
    focused_text = extract_relevant_context(full_text, search_keywords)

    # 2. TARGETED SENTIMENT
    # Determine the sentiment direction specifically targeting the brand and product
    sent_labels = [
        f"This text is negative about the {target_brand} {product}.",
        f"This text prefers a competitor over the {target_brand} {product}.",
        f"This text is positive about the {target_brand} {product}.",
        f"This text is completely neutral about the {target_brand} {product}."
    ]
    
    res_sent = zero_shot_pipeline(focused_text, candidate_labels=sent_labels)
    top_sent = res_sent['labels'][0]
    raw_sent_score = res_sent['scores'][0]

    if "negative" in top_sent or "prefers a competitor" in top_sent:
        sentiment, score = "NEGATIVE", -raw_sent_score
    elif "positive" in top_sent:
        sentiment, score = "POSITIVE", raw_sent_score
    else:
        sentiment, score = "NEUTRAL", 0.0

    # 3. ACCURACY GUARDRAILS
    # Weak classification scores on non-opinionated intents are forced to neutral
    if intent in ["QUESTION", "REQUEST", "DISCUSSION"]:
        if sentiment in ["POSITIVE", "NEGATIVE"] and abs(score) < 0.60:
            sentiment = "NEUTRAL"
            score = 0.0
            
    # Marketing and sales posts are forced to neutral to ignore promotional noise
    if intent == "SALE":
        sentiment = "NEUTRAL"
        score = 0.0

    # 4. HARDENED FEATURE ABSA
    # Loop over individual features and compute specific feature sentiments
    feature_results = {}
    for feature in features:
        if feature.lower() in focused_text.lower():
            context_text = f"We are evaluating the {feature} of the product. Text: {focused_text}" 
            labels = [
                f"The {feature} is described positively. It is good, great, fast, or comfortable.", 
                f"The {feature} is described negatively. It is bad, broken, expensive, or has issues.", 
                f"The {feature} is mentioned, but no strong opinion is given."
            ]
            result = zero_shot_pipeline(context_text, candidate_labels=labels)
            top_f = result['labels'][0]
            f_score = result['scores'][0] 
            
            if "negatively" in top_f: f_val, f_lab = -f_score, "NEGATIVE"
            elif "positively" in top_f: f_val, f_lab = f_score, "POSITIVE"
            else: f_val, f_lab = 0.0, "NEUTRAL"
                
            feature_results[feature] = {"label": f_lab, "score": round(f_val, 3)}

    # 5. MIXED SENTIMENT CONFLICT RESOLUTION
    # Resolve conflicting sentiments (both positive and negative features, or contrast words present)
    has_pos = any(f['label'] == 'POSITIVE' for f in feature_results.values())
    has_neg = any(f['label'] == 'NEGATIVE' for f in feature_results.values())
    
    padded_text = f" {focused_text.lower()} "
    contrasting_words = [" but ", " however ", " although ", " even though ", " despite "]
    has_contrast = any(word in padded_text for word in contrasting_words)

    if has_pos and has_neg:
        sentiment = "MIXED"
        score = 0.0
    elif has_contrast and (has_pos or has_neg) and sentiment != "NEUTRAL":
        sentiment = "MIXED"
        score = 0.0

    return intent, sentiment, round(score, 3), feature_results, is_sarcastic

@app.post("/analyze")
def analyze_post(post: Post):
    try:
        text = post.content.strip()
        if not text: raise HTTPException(status_code=400, detail="Empty text provided.")

        safety_status = get_content_safety(text)
        if safety_status != "SAFE":
            return {"safety_status": safety_status, "intent": "N/A", "sentiment": "N/A", "score": 0.0, "feature_sentiments": {}, "keywords": [], "is_sarcastic": False}

        intent, sentiment, score, feature_results, is_sarcastic = analyze_decoupled_nlp(text, post.target_brand, post.product, post.features)

        raw_keywords = kw_model.extract_keywords(text, keyphrase_ngram_range=(1, 2), stop_words='english', top_n=5)
        keywords = [kw[0] for kw in raw_keywords]

        return {
            "safety_status": safety_status,
            "intent": intent,
            "sentiment": sentiment,
            "score": score,
            "feature_sentiments": feature_results,
            "keywords": keywords,
            "is_sarcastic": is_sarcastic
        }

    except Exception as e:
        logger.error(f"Error during analysis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("jv:app", host="0.0.0.0", port=8001, log_level="info", workers=1)