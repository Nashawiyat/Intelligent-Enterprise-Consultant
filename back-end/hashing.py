import bcrypt

def hash_password(password):
    pass_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()

    return bcrypt.hashpw(pass_bytes, salt)

def verify_hash(password, hash):
    pass_bytes = password.encode('utf-8')
    
    return bcrypt.checkpw(pass_bytes, hash)