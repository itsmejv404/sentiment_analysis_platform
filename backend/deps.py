from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import jwt

from backend.security import decode_token
from backend.db.models import User, TenantUser, Tenant
from backend.db.db import get_db
from backend.scoping import tenant_scope_options
security = HTTPBearer()
MIN_CREDITS_FOR_ACTIVE_ORG = 100


def get_current_user(
    request: Request,
    creds: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    try:
        payload = decode_token(creds.credentials)
        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )

        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )

        tenant_id_header = request.headers.get("x-tenant-id")
        
        if tenant_id_header:
            try:
                tenant_id = int(tenant_id_header)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid X-Tenant-Id header")

            tenant_user = db.query(TenantUser).filter(
                TenantUser.user_id == user.id,
                TenantUser.tenant_id == tenant_id
            ).first()
            
            if not tenant_user:
                raise HTTPException(status_code=403, detail="Not authorized for this tenant")
                
            tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
            if not tenant:
                raise HTTPException(status_code=404, detail="Tenant not found")

            owner = db.query(User).filter(User.id == tenant.owner_id).first()
            owner_credits = int(owner.credits or 0) if owner else 0
                
            user.active_tenant_id = tenant_id
            user.active_role = tenant_user.role
            user.active_tenant_is_active = bool(tenant.is_active)
            user.active_tenant_owner_credits = owner_credits
        else:
            user.active_tenant_id = None
            user.active_role = None
            user.active_tenant_is_active = None
            user.active_tenant_owner_credits = None

        return user

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired"
        )

    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}"
        )

def require_roles(roles: list):
    def wrapper(user=Depends(get_current_user)):
        if not user.active_tenant_id:
            raise HTTPException(status_code=400, detail="Missing X-Tenant-Id header")
        if getattr(user, 'active_tenant_is_active', True) is False:
            raise HTTPException(status_code=403, detail="Tenant is inactive")
        if int(getattr(user, 'active_tenant_owner_credits', 1) or 0) < MIN_CREDITS_FOR_ACTIVE_ORG:
            raise HTTPException(
                status_code=403,
                detail=f"Tenant owner has less than {MIN_CREDITS_FOR_ACTIVE_ORG} credits, processing is inactive"
            )
        if getattr(user, 'active_role', None) not in roles:
            raise HTTPException(status_code=403, detail="Permission denied for this organization")
        return user

    return wrapper

def get_tenant_db(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    return db