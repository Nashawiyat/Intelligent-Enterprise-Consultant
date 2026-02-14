from jose import jwt
from datetime import datetime, timedelta
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
        "exp": datetime.now(datetime.timezone.utc) + timedelta(minutes=60) 
    }

    token = jwt.encode(payload, SECRET_KEY, ALGORITHM)
    return token