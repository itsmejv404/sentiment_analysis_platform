from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Float, UniqueConstraint, func
from sqlalchemy.orm import relationship
from backend.db.db import Base

# 🏢 TENANT
class Tenant(Base):
    __tablename__ = "tenants"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    brand_name = Column(String, nullable=True)
    keywords = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    owner_id = Column(Integer, ForeignKey("users.id"))
    
    users = relationship("TenantUser", back_populates="tenant", cascade="all, delete-orphan")
    owner = relationship("User", back_populates="owned_tenants")

# 🔗 TENANT-USER MAPPING
class TenantUser(Base):
    __tablename__ = "tenant_users"
    tenant_id = Column(Integer, ForeignKey("tenants.id"), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    role = Column(String, default="analyst")  # admin, manager, analyst

    tenant = relationship("Tenant", back_populates="users")
    user = relationship("User", back_populates="tenants")



# 👤 USER
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, index=True)
    password_hash = Column(String)
    credits = Column(Integer, default=500)
    
    tenants = relationship("TenantUser", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")
    reset_tokens = relationship("PasswordResetToken", back_populates="user", cascade="all, delete-orphan")
    transfer_tokens = relationship("OwnershipTransferToken", back_populates="user", cascade="all, delete-orphan")
    owned_tenants = relationship("Tenant", back_populates="owner")
    payment_transactions = relationship("PaymentTransaction", back_populates="user", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint('username', name='uix_user_username'),
    )


# 📊 AUDIT LOG
class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    tenant_id = Column(Integer, ForeignKey("tenants.id"))
    action = Column(String)
    endpoint = Column(String)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    user = relationship("User", back_populates="audit_logs")


# 🔐 RESET TOKEN
class PasswordResetToken(Base):
    __tablename__ = "reset_tokens"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    token = Column(String, index=True)
    expires_at = Column(DateTime(timezone=True))
    used = Column(Boolean, default=False)
    user = relationship("User", back_populates="reset_tokens")

# 🔄 OWNERSHIP TRANSFER TOKEN
class OwnershipTransferToken(Base):
    __tablename__ = "transfer_tokens"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id")) # Target user being invited
    tenant_id = Column(Integer, ForeignKey("tenants.id"))
    token = Column(String, index=True)
    expires_at = Column(DateTime(timezone=True))
    used = Column(Boolean, default=False)
    user = relationship("User", back_populates="transfer_tokens")
    tenant = relationship("Tenant")


# 📈 PRODUCT SENTIMENT
class ProductSentiment(Base):
    __tablename__ = "product_sentiments"
    id = Column(Integer, primary_key=True)
    post_id = Column(String, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"))
    product = Column(String, index=True)
    content = Column(String)
    intent = Column(String)
    sentiment = Column(String)
    overall_score = Column(Float)
    feature_sentiments = Column(String)
    keywords = Column(String)
    safety_status = Column(String)
    is_sarcastic = Column(Boolean)
    is_crowd_sourced = Column(Boolean)
    post_createdat = Column(DateTime(timezone=True))
    content_hash = Column(String)
    engagement = Column(Integer, default=0)
    tenant = relationship("Tenant")
    __table_args__ = (
        UniqueConstraint('post_id', 'tenant_id', name='uix_post_tenant'),
    )


# ⚠️ TENANT ALERT LOG
class TenantAlertLog(Base):
    __tablename__ = "tenant_alert_logs"
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"))
    alert_type = Column(String)  # 'high_negative_70', 'high_positive_70'
    triggered_at = Column(DateTime(timezone=True), server_default=func.now())
    tenant = relationship("Tenant")


class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    plan_id = Column(String, nullable=False)
    amount_paise = Column(Integer, nullable=False)
    currency = Column(String, nullable=False, default="INR")
    credits = Column(Integer, nullable=False)
    status = Column(String, nullable=False, default="created")
    receipt = Column(String, nullable=False, unique=True, index=True)
    order_id = Column(String, nullable=False, unique=True, index=True)
    payment_id = Column(String, nullable=True, unique=True, index=True)
    signature = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    paid_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="payment_transactions")