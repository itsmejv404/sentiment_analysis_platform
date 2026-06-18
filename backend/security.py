from passlib.context import CryptContext
import jwt
from datetime import datetime, timedelta, timezone
from backend import config

SECRET = config.SECRET_KEY
ALGO = config.ALGORITHM

pwd = CryptContext(
    schemes=["argon2"],
    deprecated="auto"
)

def hash_password(p):
    return pwd.hash(p)

def verify_password(p, h):
    return pwd.verify(p, h)


def create_token(user):
    return jwt.encode({
        "sub": str(user.id),
        "exp": datetime.now(timezone.utc) + timedelta(days=1)
    }, SECRET, algorithm=ALGO)


def decode_token(token):
    return jwt.decode(token, SECRET, algorithms=[ALGO])