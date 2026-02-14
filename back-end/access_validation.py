from typing import Annotated
from token_cryptography import decodeToken
from fastapi import Header, HTTPException, Depends
from db_helper_functions import isModeAdmin

def getUserFromToken(session_token: Annotated[str | None, Header()] = None):
    decoded = decodeToken(session_token)
    if decoded is None:
        raise HTTPException(
            detail="User token not valid. User may be logged out.",
            status_code=401
        )
    return decoded["sub"]

def admin_access_required(username: str = Depends(getUserFromToken)):
    if not isModeAdmin(username):
        raise HTTPException(
            detail="Admin priviledge required. Access denied.",
            status_code=403
        )
    return username