from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_, func, case
import secrets
import math
from datetime import datetime, timedelta, timezone

from backend.deps import require_roles, get_current_user
from backend.db.db import get_db
from backend.db.models import User, PasswordResetToken, ProductSentiment, AuditLog, TenantUser, OwnershipTransferToken, Tenant, TenantAlertLog
import backend.schema as schema
from backend.celery.tasks import send_invite_email, send_organization_deletion_email
from backend.groq.groq_insights import extract_keywords, fetch_sentiment_matches, summarize_matches
from backend import config

router = APIRouter()
MIN_CREDITS_FOR_ACTIVE_ORG = 100


def _invite_user_to_tenant(
    *,
    tenant_id: int,
    request: schema.InviteUserRequest,
    inviter: User,
    db: Session,
):
    email = request.email.lower().strip()
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")

    existing_user = db.query(User).filter(User.username == email).first()
    if existing_user:
        already_mapped = db.query(TenantUser).filter(
            TenantUser.user_id == existing_user.id,
            TenantUser.tenant_id == tenant_id
        ).first()
        if already_mapped:
            raise HTTPException(status_code=400, detail="User is already in this organization")

        tenant_user = TenantUser(
            tenant_id=tenant_id,
            user_id=existing_user.id,
            role=request.role or "analyst"
        )
        db.add(tenant_user)

        log = AuditLog(
            user_id=inviter.id,
            tenant_id=tenant_id,
            action="INVITE_EXISTING_USER",
            endpoint="/admin/users"
        )
        db.add(log)
        db.commit()
        return {"success": True, "msg": "User added to organization directly"}

    # Create placeholder user and invitation token for password setup
    new_user = User(
        username=email,
        password_hash=""
    )
    db.add(new_user)
    db.flush()

    tenant_user = TenantUser(
        tenant_id=tenant_id,
        user_id=new_user.id,
        role=request.role or "analyst"
    )
    db.add(tenant_user)

    token = secrets.token_urlsafe(32)
    reset = PasswordResetToken(
        user_id=new_user.id,
        token=token,
        expires_at=datetime.utcnow() + timedelta(days=1)
    )
    db.add(reset)

    invite_link = f"{config.FRONTEND_URL}/reset-password?token={token}"
    send_invite_email.delay(new_user.username, invite_link)

    log = AuditLog(
        user_id=inviter.id,
        tenant_id=tenant_id,
        action="INVITE_USER",
        endpoint="/admin/users"
    )
    db.add(log)
    db.commit()

    return {"success": True, "msg": "User invited successfully"}


@router.get("/admin/dashboard")
def admin_dashboard(user=Depends(require_roles(["admin"]))):
    return {"msg": "Admin only data"}


@router.get("/analytics")
def analytics(
    page: int = 1,
    limit: int = 10,
    keywords: str = None,
    search: str = None,
    timeframe: str = None,     
    start_time: str = None,    
    end_time: str = None,      
    sort_by: str = "time_desc", 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["manager", "admin", "analyst"]))
):
    query = db.query(ProductSentiment).filter(
        ProductSentiment.tenant_id == current_user.active_tenant_id
    )
    if keywords:
        kw_list = [k.strip() for k in keywords.split(",") if k.strip()]
        if kw_list:
            query = query.filter(ProductSentiment.product.in_(kw_list))

    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(
                ProductSentiment.content.ilike(pattern),
                ProductSentiment.product.ilike(pattern)
            )
        )

    now = datetime.utcnow()
    if timeframe == "1h":
        query = query.filter(ProductSentiment.post_createdat >= now - timedelta(hours=1))
    elif timeframe == "12h":
        query = query.filter(ProductSentiment.post_createdat >= now - timedelta(hours=12))
    elif timeframe == "24h":
        query = query.filter(ProductSentiment.post_createdat >= now - timedelta(hours=24))
    elif timeframe == "custom" and start_time and end_time:
        try:
            dt_start = datetime.fromisoformat(start_time)
            dt_end = datetime.fromisoformat(end_time)
            query = query.filter(
                ProductSentiment.post_createdat >= dt_start,
                ProductSentiment.post_createdat <= dt_end
            )
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_time or end_time format. Use ISO 8601.")

    filtered_query = query

    if sort_by == "time_asc":
        query = query.order_by(ProductSentiment.post_createdat.asc())
    elif sort_by == "score_desc":
        query = query.order_by(ProductSentiment.overall_score.desc())
    elif sort_by == "score_asc":
        query = query.order_by(ProductSentiment.overall_score.asc())
    elif sort_by == "engagement_desc":
        query = query.order_by(ProductSentiment.engagement.desc())
    else: 
        query = query.order_by(ProductSentiment.post_createdat.desc())

    total = query.count()
    
    stats = db.query(
        func.count(ProductSentiment.id).filter(ProductSentiment.sentiment == "POSITIVE").label("positive"),
        func.count(ProductSentiment.id).filter(ProductSentiment.sentiment == "NEGATIVE").label("negative"),
        func.count(ProductSentiment.id).filter(ProductSentiment.sentiment == "NEUTRAL").label("neutral"),
    ).filter(ProductSentiment.tenant_id == current_user.active_tenant_id)
    
    positive = query.filter(ProductSentiment.sentiment == "POSITIVE").count()
    negative = query.filter(ProductSentiment.sentiment == "NEGATIVE").count()
    neutral = query.filter(ProductSentiment.sentiment == "NEUTRAL").count()
    mixed = total - positive - negative - neutral

    paginated_rows = query.offset((page - 1) * limit).limit(limit).all()

    trend_rows = filtered_query.order_by(ProductSentiment.post_createdat.desc()).limit(100).all()

    prediction = {"majority": None, "trend": "STABLE", "direction": None}
    if total > 0:
        majority = max(
            [("POSITIVE", positive), ("NEGATIVE", negative), ("NEUTRAL", neutral)],
            key=lambda x: x[1]
        )[0]
        prediction["majority"] = majority

        if len(trend_rows) >= 6:
            midpoint = len(trend_rows) // 2
            recent_half = trend_rows[:midpoint]
            older_half = trend_rows[midpoint:]

            def sentiment_score(rows):
                if not rows: return 0
                pos = sum(1 for r in rows if r.sentiment == "POSITIVE")
                neg = sum(1 for r in rows if r.sentiment == "NEGATIVE")
                return (pos - neg) / len(rows)  # positive = trending positive

            recent_score = sentiment_score(recent_half)
            older_score = sentiment_score(older_half)
            delta = recent_score - older_score

            if delta > 0.15:
                prediction["trend"] = "IMPROVING"
                prediction["direction"] = "↑"
            elif delta < -0.15:
                prediction["trend"] = "WORSENING"
                prediction["direction"] = "↓"
            else:
                prediction["trend"] = "STABLE"
                prediction["direction"] = "→"


    recent_mentions = [
        {
            "id": s.id,
            "content": s.content,
            "sentiment": s.sentiment,
            "intent": s.intent,
            "product": s.product,
            "overall_score": s.overall_score,
            "engagement": s.engagement or 0,
            "post_createdat": s.post_createdat.isoformat() if s.post_createdat else None
        }
        for s in paginated_rows
    ]

    chart_data = [
        {"t": s.post_createdat.isoformat(), "s": s.sentiment}
        for s in filtered_query.order_by(ProductSentiment.post_createdat.desc()).limit(500).all()
        if s.post_createdat
    ]

    pos_pct = round((positive / total * 100), 1) if total else 0
    neg_pct = round((negative / total * 100), 1) if total else 0
    neu_pct = round((neutral / total * 100), 1) if total else 0

    return {
        "summary": {
            "total_mentions": total,
            "positive": positive,
            "negative": negative,
            "neutral": neutral,
            "mixed": mixed,
            "positive_pct": pos_pct,
            "negative_pct": neg_pct,
            "neutral_pct": neu_pct,
        },
        "prediction": prediction,
        "recent_mentions": recent_mentions,
        "chart_data": chart_data,
        "pagination": {
            "page": page,
            "limit": limit,
            "total_pages": math.ceil(total / limit) if limit > 0 else 1
        }
    }


@router.post("/admin/sentiment-query")
def sentiment_query(
    request: schema.SentimentQueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["manager", "admin", "analyst"])),
):
    query_text = request.query.strip()
    if not query_text:
        raise HTTPException(status_code=400, detail="Query text is required")

    tenant = db.query(Tenant).filter(Tenant.id == current_user.active_tenant_id).first()
    tenant_keywords = [k.strip() for k in (tenant.keywords or "").split(",") if k.strip()] if tenant else []

    extracted = extract_keywords(query_text, tenant_keywords)
    rows = fetch_sentiment_matches(
        db=db,
        tenant_id=current_user.active_tenant_id,
        keywords=extracted.get("keywords", []),
        timeframe=request.timeframe,
    )

    insights = summarize_matches(
        rows=rows,
        query=query_text,
        focus=extracted.get("focus", query_text),
        keywords=extracted.get("keywords", []),
        summary_hint=extracted.get("summary_hint", ""),
    )

    focus = extracted.get("focus", query_text)
    keywords = extracted.get("keywords", [])

    return {
        "query": query_text,
        "focus": focus,
        "keywords": keywords,
        "timeframe": request.timeframe,
        "summary_text": insights["summary_text"],
        "summary": insights["summary"],
        "chart_data": insights["chart_data"],
        "visual_summary": insights["visual_summary"],
        "sample_posts": insights["sample_posts"],
        "top_products": insights["top_products"],
        "average_score": insights["average_score"],
        "representative_image": None,
    }

@router.post("/admin/users")
def invite_user(request: schema.InviteUserRequest, db: Session = Depends(get_db), current_user: User = Depends(require_roles(["admin"]))):
    return _invite_user_to_tenant(
        tenant_id=current_user.active_tenant_id,
        request=request,
        inviter=current_user,
        db=db,
    )


@router.post("/admin/organizations/{tenant_id}/users")
def invite_user_to_organization(
    tenant_id: int,
    request: schema.InviteUserToTenantRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    membership = db.query(TenantUser).filter(
        TenantUser.user_id == current_user.id,
        TenantUser.tenant_id == tenant_id
    ).first()
    if not membership or membership.role != "admin":
        raise HTTPException(status_code=403, detail="Only organization admins can invite users")

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Organization not found")

    return _invite_user_to_tenant(
        tenant_id=tenant_id,
        request=schema.InviteUserRequest(email=request.email, role=request.role),
        inviter=current_user,
        db=db,
    )


@router.patch("/admin/organizations/{tenant_id}/status")
def update_organization_status(
    tenant_id: int,
    request: schema.OrganizationStatusUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Organization not found")

    if tenant.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the organization owner can change status")

    if request.is_active and int(current_user.credits or 0) < MIN_CREDITS_FOR_ACTIVE_ORG:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot activate organization with less than {MIN_CREDITS_FOR_ACTIVE_ORG} credits"
        )

    tenant.is_active = request.is_active
    action = "ORGANIZATION_ACTIVATED" if request.is_active else "ORGANIZATION_INACTIVATED_MANUAL"
    log = AuditLog(
        user_id=current_user.id,
        tenant_id=tenant.id,
        action=action,
        endpoint=f"/admin/organizations/{tenant_id}/status"
    )
    db.add(log)
    db.commit()
    db.refresh(tenant)

    return {
        "success": True,
        "msg": "Organization status updated successfully",
        "tenant_id": tenant.id,
        "is_active": tenant.is_active,
    }


@router.delete("/admin/organizations/{tenant_id}")
def delete_organization(
    tenant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Organization not found")

    if tenant.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the organization owner can delete this organization")

    tenant_name = tenant.brand_name or tenant.name
    deleted_org_details = {
        "id": tenant.id,
        "name": tenant.name,
        "brand_name": tenant.brand_name,
        "keywords": tenant.keywords,
        "is_active": tenant.is_active,
    }

    db.query(ProductSentiment).filter(ProductSentiment.tenant_id == tenant_id).delete(synchronize_session=False)
    db.query(TenantAlertLog).filter(TenantAlertLog.tenant_id == tenant_id).delete(synchronize_session=False)
    db.query(OwnershipTransferToken).filter(OwnershipTransferToken.tenant_id == tenant_id).delete(synchronize_session=False)
    db.query(TenantUser).filter(TenantUser.tenant_id == tenant_id).delete(synchronize_session=False)
    db.query(AuditLog).filter(AuditLog.tenant_id == tenant_id).delete(synchronize_session=False)

    db.delete(tenant)

    db.add(
        AuditLog(
            user_id=current_user.id,
            tenant_id=None,
            action="ORGANIZATION_DELETED",
            endpoint=f"/admin/organizations/{tenant_id}"
        )
    )

    db.commit()

    send_organization_deletion_email.delay(current_user.username, deleted_org_details)

    return {
        "success": True,
        "msg": f"Organization '{tenant_name}' and all related data deleted successfully",
        "tenant_id": tenant_id,
    }

@router.post("/admin/transfer-ownership")
def transfer_ownership(request: schema.TransferOwnershipRequest, db: Session = Depends(get_db), current_user: User = Depends(require_roles(["admin"]))):
    # Ensure current user is the actual OWNER, not just an admin
    tenant = db.query(Tenant).filter(Tenant.id == current_user.active_tenant_id).first()
    if tenant.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the organization owner can transfer ownership")
        
    target_user = db.query(User).filter(User.username == request.email.lower()).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found. They must register first.")
        
    # Create transfer token
    token = secrets.token_urlsafe(32)
    transfer = OwnershipTransferToken(
        user_id=target_user.id,
        tenant_id=tenant.id,
        token=token,
        expires_at=datetime.utcnow() + timedelta(days=2) # 48 hours to accept
    )
    db.add(transfer)
    db.commit()
    
    # In a real app, send an email here.
    return {"success": True, "msg": "Ownership transfer initiated", "token": token}

@router.post("/admin/accept-transfer")
def accept_transfer(token: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    transfer = db.query(OwnershipTransferToken).filter(
        OwnershipTransferToken.token == token,
        OwnershipTransferToken.used == False
    ).first()
    
    if not transfer or transfer.expires_at < datetime.utcnow() or transfer.user_id != current_user.id:
        raise HTTPException(status_code=400, detail="Invalid or expired transfer token")
        
    tenant = db.query(Tenant).filter(Tenant.id == transfer.tenant_id).first()
    
    # Update ownership
    tenant.owner_id = current_user.id
    transfer.used = True
    
    # Ensure the new owner is an admin
    tenant_user = db.query(TenantUser).filter(TenantUser.user_id == current_user.id, TenantUser.tenant_id == tenant.id).first()
    if not tenant_user:
        tenant_user = TenantUser(tenant_id=tenant.id, user_id=current_user.id, role="admin")
        db.add(tenant_user)
    else:
        tenant_user.role = "admin"
        
    db.commit()
    return {"success": True, "msg": "Ownership transfer accepted successfully"}
