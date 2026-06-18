import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import make_pipeline
from sklearn import metrics
import joblib

print("Loading 3-Class dataset...")
# Make sure you have your combined_data.csv ready!
df = pd.read_csv('combined_data.csv')

X_train, X_test, y_train, y_test = train_test_split(
    df['message'], df['label'], test_size=0.2, random_state=42
)

print("Training the 3-Class AI Model...")
model = make_pipeline(TfidfVectorizer(stop_words='english', min_df=2), MultinomialNB())
model.fit(X_train, y_train)

print("Evaluating Accuracy...")
y_pred = model.predict(X_test)
print("\n--- Classification Report ---")
print(metrics.classification_report(y_test, y_pred, target_names=['Normal (0)', 'Promo (1)', 'Adult (2)']))

EXPORT_PATH = "spam_classifier_v3.pkl"
joblib.dump(model, EXPORT_PATH)
print(f"\n✅ Upgraded model successfully saved to: {EXPORT_PATH}")