from pydantic import BaseModel
from typing import Optional

class LoginRequest(BaseModel):
    username: str  # This is the email
    password: str

class ForgotPasswordRequest(BaseModel):
    email: str

class RegisterRequest(BaseModel):
    username: str
    password: str
    role: Optional[str] = "analyst"

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

class InviteUserRequest(BaseModel):
    email: str
    role: Optional[str] = "analyst"

class InviteUserToTenantRequest(BaseModel):
    email: str
    role: Optional[str] = "analyst"

class TenantUpdateRequest(BaseModel):
    brand_name: Optional[str] = None
    keywords: Optional[str] = None

class CreateOrganizationRequest(BaseModel):
    name: str
    brand_name: Optional[str] = None
    keywords: Optional[str] = None

class OrganizationStatusUpdateRequest(BaseModel):
    is_active: bool

class TransferOwnershipRequest(BaseModel):
    email: str


class CreateCreditOrderRequest(BaseModel):
    plan_id: str


class VerifyCreditPaymentRequest(BaseModel):
    plan_id: str
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


class DeleteAccountRequest(BaseModel):
    feedback: Optional[str] = None


class SentimentQueryRequest(BaseModel):
    query: str
    timeframe: Optional[str] = None