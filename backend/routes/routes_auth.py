from fastapi import APIRouter, Depends, HTTPException
from backend import config
from sqlalchemy.orm import Session
from backend.db.models import User, PasswordResetToken, Tenant, TenantUser, AuditLog
from backend.security import verify_password, hash_password, create_token
from backend.celery.tasks import send_reset_email, send_account_deletion_feedback
from backend.deps import get_current_user
from datetime import datetime, timedelta, timezone
import secrets
import backend.schema as schema
from backend.db.db import get_db
router = APIRouter()

ORG_CREATION_COST = 100
MIN_CREDITS_FOR_ACTIVE_ORG = 100


@router.post("/register")
def register(request: schema.RegisterRequest, db: Session = Depends(get_db)):
    email = request.username.lower()

    # 1. Check if user exists ANYWHERE by email
    existing_user = db.query(User).filter(User.username == email).first()

    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")

    # 2. Create user (Default 500 credits)
    new_user = User(
        username=email,
        password_hash=hash_password(request.password),
        credits=500
    )
    db.add(new_user)
    db.commit()

    return {
        "success": True,
        "msg": "User created successfully",
        "user_id": new_user.id
    }

@router.post("/organization")
def create_organization(request: schema.CreateOrganizationRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # 1. Check if name exists
    existing = db.query(Tenant).filter(Tenant.name == request.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Organization name already taken")

    # 2. Charge credits for organization creation
    if current_user.credits < ORG_CREATION_COST:
        raise HTTPException(
            status_code=400,
            detail=f"Not enough credits. Creating an organization costs {ORG_CREATION_COST} credits."
        )

    current_user.credits -= ORG_CREATION_COST

    # 3. Create organization with current_user as owner
    tenant = Tenant(
        name=request.name,
        brand_name=request.brand_name,
        keywords=request.keywords,
        owner_id=current_user.id,
        is_active=current_user.credits >= MIN_CREDITS_FOR_ACTIVE_ORG
    )
    db.add(tenant)
    db.flush()

    # 4. Add current user as admin
    tenant_user = TenantUser(
        tenant_id=tenant.id,
        user_id=current_user.id,
        role="admin"
    )
    db.add(tenant_user)

    # 5. Audit Log
    log = AuditLog(
        user_id=current_user.id,
        tenant_id=tenant.id,
        action="CREATE_ORGANIZATION",
        endpoint="/organization"
    )
    db.add(log)
    db.commit()
    db.refresh(tenant)
    db.refresh(current_user)

    return {
        "success": True,
        "msg": "Organization created successfully",
        "tenant_id": tenant.id,
        "charged_credits": ORG_CREATION_COST,
        "remaining_credits": current_user.credits,
        "is_active": tenant.is_active,
    }

@router.post("/login")
def login(request: schema.LoginRequest, db: Session = Depends(get_db)):
    username = request.username.lower()
    user = db.query(User).filter(
        User.username == username,
    ).first()

    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(401, "Invalid credentials")

    return {
        "success": True,
        "access_token": create_token(user),
        "token_type": "bearer"
    }

@router.post("/forgot-password")
def forgot_password(request: schema.ForgotPasswordRequest, db: Session = Depends(get_db)):
    email = request.email.lower()
    user = db.query(User).filter(User.username == email).first()

    if not user:
        # Standard security practice: don't reveal if user exists
        return {"success": True, "msg": "If the account exists, a reset link will be sent."}

    token = secrets.token_urlsafe(32)

    reset = PasswordResetToken(
        user_id=user.id,
        token=token,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=15)
    )

    db.add(reset)
    db.commit()

    # In production, this would be a frontend URL
    reset_link = f"{config.FRONTEND_URL}/reset-password?token={token}"
    print(reset_link)
    send_reset_email.delay(user.username, reset_link)

    return {"success": True, "msg": "Reset link sent to your email."}

@router.post("/reset-password")
def reset_password(request: schema.ResetPasswordRequest, db: Session = Depends(get_db)):
    token_record = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == request.token,
        PasswordResetToken.used == False
    ).first()

    if not token_record or token_record.expires_at < datetime.now(timezone.utc):
        raise HTTPException(400, "Invalid or expired reset token")

    user = db.query(User).filter(User.id == token_record.user_id).first()
    if not user:
         raise HTTPException(404, "User not found")

    user.password_hash = hash_password(request.new_password)
    token_record.used = True

    db.commit()

    return {"success": True, "msg": "Password updated successfully"}

@router.get("/me")
def me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Find all tenants this user belongs to
    tenant_users = db.query(TenantUser).filter(TenantUser.user_id == current_user.id).all()
    
    organizations = []
    for tu in tenant_users:
        t = db.query(Tenant).filter(Tenant.id == tu.tenant_id).first()
        if t:
            organizations.append({
                "id": t.id,
                "name": t.name,
                "brand_name": t.brand_name,
                "keywords": t.keywords,
                "is_active": t.is_active,
                "owner_id": t.owner_id,
                "role": tu.role
            })
            
    return {
        "id": current_user.id,
        "username": current_user.username,
        "credits": current_user.credits,
        "active_tenant_id": getattr(current_user, 'active_tenant_id', None),
        "organizations": organizations
    }

@router.patch("/tenant")
def update_tenant(request: schema.TenantUpdateRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not current_user.active_tenant_id:
        raise HTTPException(status_code=400, detail="Missing X-Tenant-Id header")

    if getattr(current_user, 'active_tenant_is_active', True) is False:
        raise HTTPException(status_code=403, detail="Tenant is inactive due to insufficient credits")
        
    if current_user.active_role != "admin":
        raise HTTPException(status_code=403, detail="Must be admin")
        
    tenant = db.query(Tenant).filter(Tenant.id == current_user.active_tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
        
    if request.brand_name is not None:
        tenant.brand_name = request.brand_name
    if request.keywords is not None:
        tenant.keywords = request.keywords
        
    db.commit()
    db.refresh(tenant)
    return {"success": True, "msg": "Tenant updated successfully"}

@router.delete("/me")
def delete_me(
    request: schema.DeleteAccountRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    send_account_deletion_feedback.delay(current_user.username, (request.feedback if request else "") or "")

    # Deleting self entirely
    db.delete(current_user)
    db.commit()
    return {"success": True, "msg": "User deleted successfully"}