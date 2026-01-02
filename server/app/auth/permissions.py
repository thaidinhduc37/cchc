from enum import Enum
from typing import List
from fastapi import Request, HTTPException

class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"

def check_permission(allowed_roles: List[UserRole]):
    """Permission decorator"""
    def decorator(func):
        async def wrapper(request: Request, *args, **kwargs):
            user = request.state.user
            if not user:
                raise HTTPException(status_code=403, detail="Unauthorized")
                
            user_role = UserRole(user.get("role", "guest"))
            if user_role not in allowed_roles:
                raise HTTPException(status_code=403, detail="Insufficient permissions")
                
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator