from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"])

def hash_password(password):
    password = password[:72]
    return pwd_context.hash(password)

def verify_hash(password, hash):
    password = password[:72]
    return pwd_context.verify(password, hash)