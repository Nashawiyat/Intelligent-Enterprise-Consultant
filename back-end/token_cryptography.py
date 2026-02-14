from jose import jwt
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
import os

load_dotenv()
try: 
    SECRET_KEY = os.getenv("SECRET_KEY")
    ALGORITHM = os.getenv("ALGORITHM")
except Exception as e:
    raise e

def generateToken(username):
    payload = {
        "sub": username,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=60) 
    }

    token = jwt.encode(payload, SECRET_KEY, ALGORITHM)
    return token

def decodeToken(token):
    try:
        return jwt.decode(token, SECRET_KEY, ALGORITHM)
    except Exception as e:
        return None