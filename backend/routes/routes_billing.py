from datetime import datetime, timezone
import importlib
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend import config
import backend.schema as schema
from backend.db.db import get_db
from backend.deps import get_current_user
from backend.db.models import AuditLog, PaymentTransaction, User

try:
    import razorpay
except ImportError:  # pragma: no cover
    razorpay = None

router = APIRouter(prefix="/billing", tags=["billing"])

CREDIT_PLANS = {
    "starter_1000": {
        "id": "starter_1000",
        "credits": 1000,
        "price_rs": 500,
        "amount_paise": 50000,
        "currency": "INR",
        "label": "1000 credits for 500 Rs",
    },
    "growth_5000": {
        "id": "growth_5000",
        "credits": 5000,
        "price_rs": 2000,
        "amount_paise": 200000,
        "currency": "INR",
        "label": "5000 credits for 2000 Rs",
    },
    "scale_30000": {
        "id": "scale_30000",
        "credits": 30000,
        "price_rs": 10000,
        "amount_paise": 1000000,
        "currency": "INR",
        "label": "30000 credits for 10000 Rs",
    },
}


def _get_plan(plan_id: str):
    plan = CREDIT_PLANS.get(plan_id)
    if not plan:
        raise HTTPException(status_code=400, detail="Invalid credit plan")
    return plan


def _get_razorpay_client():
    global razorpay
    if razorpay is None:
        try:
            razorpay = importlib.import_module("razorpay")
        except ImportError:
            razorpay = None

    if razorpay is None:
        raise HTTPException(
            status_code=503,
            detail="Razorpay SDK is not installed on backend. Install with: pip install razorpay",
        )

    if not config.RAZORPAY_KEY_ID or not config.RAZORPAY_KEY_SECRET:
        raise HTTPException(
            status_code=503,
            detail="Razorpay is not configured. Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET as environment variables",
        )

    return razorpay.Client(auth=(config.RAZORPAY_KEY_ID, config.RAZORPAY_KEY_SECRET))


@router.get("/plans")
def get_credit_plans(current_user: User = Depends(get_current_user)):
    _ = current_user
    return {"plans": list(CREDIT_PLANS.values())}


@router.post("/razorpay/order")
def create_razorpay_credit_order(
    request: schema.CreateCreditOrderRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan = _get_plan(request.plan_id)
    client = _get_razorpay_client()

    receipt = f"u{current_user.id}_{secrets.token_hex(12)}"

    try:
        order = client.order.create(
            {
                "amount": plan["amount_paise"],
                "currency": plan["currency"],
                "receipt": receipt,
                "notes": {
                    "user_id": str(current_user.id),
                    "plan_id": plan["id"],
                    "credits": str(plan["credits"]),
                },
            }
        )
    except Exception:
        raise HTTPException(status_code=502, detail="Failed to create Razorpay order")

    transaction = PaymentTransaction(
        user_id=current_user.id,
        plan_id=plan["id"],
        amount_paise=plan["amount_paise"],
        currency=plan["currency"],
        credits=plan["credits"],
        status="created",
        receipt=receipt,
        order_id=order["id"],
    )
    db.add(transaction)
    db.commit()

    return {
        "order_id": order["id"],
        "amount": plan["amount_paise"],
        "currency": plan["currency"],
        "plan_id": plan["id"],
        "credits": plan["credits"],
        "key_id": config.RAZORPAY_KEY_ID,
    }


@router.post("/razorpay/verify")
def verify_razorpay_credit_payment(
    request: schema.VerifyCreditPaymentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _ = _get_plan(request.plan_id)
    client = _get_razorpay_client()

    transaction = (
        db.query(PaymentTransaction)
        .filter(
            PaymentTransaction.order_id == request.razorpay_order_id,
            PaymentTransaction.user_id == current_user.id,
        )
        .with_for_update()
        .first()
    )

    if not transaction:
        raise HTTPException(status_code=404, detail="Payment order not found")

    if transaction.plan_id != request.plan_id:
        raise HTTPException(status_code=400, detail="Plan mismatch for payment order")

    if transaction.status == "paid":
        if transaction.payment_id == request.razorpay_payment_id:
            return {
                "success": True,
                "msg": "Payment already verified",
                "added_credits": transaction.credits,
                "current_credits": current_user.credits,
            }
        raise HTTPException(status_code=409, detail="Order already settled with a different payment")

    try:
        client.utility.verify_payment_signature(
            {
                "razorpay_order_id": request.razorpay_order_id,
                "razorpay_payment_id": request.razorpay_payment_id,
                "razorpay_signature": request.razorpay_signature,
            }
        )
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Razorpay payment signature")

    try:
        payment = client.payment.fetch(request.razorpay_payment_id)
    except Exception:
        raise HTTPException(status_code=502, detail="Unable to validate Razorpay payment details")

    if payment.get("order_id") != request.razorpay_order_id:
        raise HTTPException(status_code=400, detail="Payment does not belong to this order")

    if int(payment.get("amount", 0)) != int(transaction.amount_paise):
        raise HTTPException(status_code=400, detail="Amount mismatch in payment")

    payment_currency = (payment.get("currency") or "").upper()
    if payment_currency != transaction.currency.upper():
        raise HTTPException(status_code=400, detail="Currency mismatch in payment")

    payment_status = (payment.get("status") or "").lower()
    if payment_status not in {"authorized", "captured"}:
        raise HTTPException(status_code=400, detail="Payment is not completed")

    current_user.credits = int(current_user.credits or 0) + int(transaction.credits)

    transaction.status = "paid"
    transaction.payment_id = request.razorpay_payment_id
    transaction.signature = request.razorpay_signature
    transaction.paid_at = datetime.now(timezone.utc)

    db.add(
        AuditLog(
            user_id=current_user.id,
            tenant_id=current_user.active_tenant_id,
            action="CREDITS_PURCHASED_RAZORPAY",
            endpoint="/billing/razorpay/verify",
        )
    )

    db.commit()
    db.refresh(current_user)

    return {
        "success": True,
        "msg": "Credits added successfully",
        "added_credits": transaction.credits,
        "current_credits": current_user.credits,
    }
