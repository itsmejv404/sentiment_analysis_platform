from celery import Celery
from backend import config

celery_app = Celery(
    "worker",
    broker=config.CELERY_BROKER_URL,
    backend=config.CELERY_RESULT_BACKEND,
    include=["backend.celery.tasks"]
)