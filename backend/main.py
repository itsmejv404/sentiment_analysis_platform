from fastapi import FastAPI
from backend.db.db import Base, engine
import backend.db.models as models
from fastapi.middleware.cors import CORSMiddleware

from backend.routes.routes_auth import router as auth_router
from backend.routes.routes_admin import router as admin_router
from backend.routes.routes_billing import router as billing_router
origins = [
    "http://localhost",
    "http://localhost:8080",
    "http://localhost:5173",
]

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(billing_router)