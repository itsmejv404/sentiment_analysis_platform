from sqlalchemy import select, event
from sqlalchemy.orm import Session, with_loader_criteria

class TenantManager:
    def __init__(self):
        self._current_tenant_id = None

    def set_tenant(self, tenant_id: int):
        self._current_tenant_id = tenant_id

    def get_tenant(self):
        return self._current_tenant_id

tenant_context = TenantManager()

def tenant_scope_options(tenant_id: int):
    if tenant_id is None:
        return []
    return [
        with_loader_criteria(
            lambda cls: hasattr(cls, "tenant_id"),
            lambda cls: cls.tenant_id == tenant_id,
            include_subclasses=True
        )
    ]

def scoped_db_query(db: Session, model, tenant_id: int):
    query = db.query(model)
    if tenant_id is not None and hasattr(model, 'tenant_id'):
        query = query.filter(model.tenant_id == tenant_id)
    return query
