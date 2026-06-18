import os
import time
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from backend.db.db import SessionLocal
from backend.db.models import Tenant, AuditLog, TenantUser, User
from backend.celery.tasks import send_low_credit_alert

ACTIVE_ORG_BILLING_COST = 100
LOW_CREDIT_THRESHOLD = ACTIVE_ORG_BILLING_COST
LOW_CREDIT_ALERT_COOLDOWN_HOURS = int(os.getenv("LOW_CREDIT_ALERT_COOLDOWN_HOURS", "24"))
RUN_INTERVAL_SECONDS = int(os.getenv("BILLING_CRON_INTERVAL_SECONDS", "5"))


def _get_admin_emails(db: Session, tenant_id: int):
    admin_ids = db.query(TenantUser.user_id).filter(
        TenantUser.tenant_id == tenant_id,
        TenantUser.role == "admin"
    ).all()
    if not admin_ids:
        return []

    user_ids = [row[0] for row in admin_ids]
    admins = db.query(User).filter(User.id.in_(user_ids)).all()
    return [u.username for u in admins if u.username]


def _inactivate_owned_tenants(db: Session, user: User):
    owned_tenants = db.query(Tenant).filter(Tenant.owner_id == user.id).all()
    inactivated_count = 0

    for tenant in owned_tenants:
        if tenant.is_active:
            tenant.is_active = False
            inactivated_count += 1
            db.add(
                AuditLog(
                    user_id=user.id,
                    tenant_id=tenant.id,
                    action="ORGANIZATION_INACTIVATED_LOW_CREDITS",
                    endpoint="billing_cron",
                )
            )

    return inactivated_count


def _should_send_low_credit_alert(db: Session, user_id: int, tenant_id: int) -> bool:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=LOW_CREDIT_ALERT_COOLDOWN_HOURS)
    recent_alert = (
        db.query(AuditLog)
        .filter(
            AuditLog.user_id == user_id,
            AuditLog.tenant_id == tenant_id,
            AuditLog.action == "LOW_CREDIT_ALERT_SENT",
            AuditLog.timestamp >= cutoff,
        )
        .first()
    )
    return recent_alert is None


def process_daily_billing():
    print(f"[{datetime.now(timezone.utc).isoformat()}] Starting organization-status billing process...")

    db: Session = SessionLocal()
    try:
        users = db.query(User).all()
        processed_users = 0

        for user in users:
            # Enforce inactive policy immediately when credits are below required minimum.
            if int(user.credits or 0) < ACTIVE_ORG_BILLING_COST:
                inactivated_count = _inactivate_owned_tenants(db, user)
                if inactivated_count:
                    print(
                        f"User {user.id} ({user.username}): inactivated {inactivated_count} owned organization(s) because credits are below {ACTIVE_ORG_BILLING_COST}"
                    )

                owned_tenants = db.query(Tenant).filter(Tenant.owner_id == user.id).all()
                inactive_owned_count = sum(1 for t in owned_tenants if not bool(t.is_active))

                for tenant in owned_tenants:
                    if not _should_send_low_credit_alert(db, user.id, tenant.id):
                        continue

                    tenant_name = tenant.brand_name or tenant.name
                    admin_emails = _get_admin_emails(db, tenant.id)
                    for email in admin_emails:
                        send_low_credit_alert.delay(email, tenant_name, user.credits, inactive_owned_count)

                    db.add(
                        AuditLog(
                            user_id=user.id,
                            tenant_id=tenant.id,
                            action="LOW_CREDIT_ALERT_SENT",
                            endpoint="billing_cron"
                        )
                    )

                processed_users += 1
                continue

            admin_tenants = (
                db.query(Tenant)
                .join(TenantUser, TenantUser.tenant_id == Tenant.id)
                .filter(
                    TenantUser.user_id == user.id,
                    TenantUser.role == "admin",
                    Tenant.is_active == True
                )
                .all()
            )

            admin_org_count = len(admin_tenants)
            if admin_org_count == 0:
                # Even if no active admin orgs, enforce inactive policy if credits dropped.
                _inactivate_owned_tenants(db, user)
                continue

            deduction = admin_org_count * ACTIVE_ORG_BILLING_COST
            previous_credits = max(0, user.credits)
            user.credits = max(0, user.credits - deduction)
            print(
                f"User {user.id} ({user.username}): {admin_org_count} active admin org(s), "
                f"deducted {deduction} credits, balance {previous_credits} -> {user.credits}"
            )

            for tenant in admin_tenants:
                log = AuditLog(
                    user_id=user.id,
                    tenant_id=tenant.id,
                    action="DAILY_ACTIVE_ORG_BILLING",
                    endpoint="billing_cron"
                )
                db.add(log)

            if user.credits <= LOW_CREDIT_THRESHOLD:
                owned_tenants = db.query(Tenant).filter(Tenant.owner_id == user.id).all()
                inactive_owned_count = sum(1 for t in owned_tenants if not bool(t.is_active))

                for tenant in owned_tenants:
                    if not _should_send_low_credit_alert(db, user.id, tenant.id):
                        continue

                    tenant_name = tenant.brand_name or tenant.name
                    admin_emails = _get_admin_emails(db, tenant.id)
                    for email in admin_emails:
                        send_low_credit_alert.delay(email, tenant_name, user.credits, inactive_owned_count)

                    log = AuditLog(
                        user_id=user.id,
                        tenant_id=tenant.id,
                        action="LOW_CREDIT_ALERT_SENT",
                        endpoint="billing_cron"
                    )
                    db.add(log)

            if user.credits < ACTIVE_ORG_BILLING_COST:
                inactivated_count = _inactivate_owned_tenants(db, user)
                if inactivated_count:
                    print(
                        f"User {user.id} ({user.username}): inactivated {inactivated_count} owned organization(s) because credits fell below {ACTIVE_ORG_BILLING_COST}"
                    )

            processed_users += 1

        db.commit()
        print(f"[{datetime.now(timezone.utc).isoformat()}] Billing process completed successfully for {processed_users} users.")

    except Exception as e:
        db.rollback()
        print(f"Error during billing process: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    print(f"Billing daemon started. Interval: {RUN_INTERVAL_SECONDS} seconds.")
    while True:
        process_daily_billing()
        time.sleep(RUN_INTERVAL_SECONDS)
