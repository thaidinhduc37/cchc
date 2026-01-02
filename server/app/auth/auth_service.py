import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from app.config.app_config import Config
from app.auth.user_management import UserManager

config = Config()

class AuthService:
    def __init__(self):
        self.user_manager = UserManager()
        self.secret_key = config.JWT_SECRET_KEY
        self.token_expire_minutes = config.TOKEN_EXPIRE_MINUTES
        self.jwt_algorithm = "HS256"
        
    async def register_user(self, email: str, password: str, fullname: str) -> Dict[str, Any]:
        """Register new user"""
        # Check if user exists
        if await self.user_manager.get_user_by_email(email):
            return {"error": "Email đã được đăng ký"}
            
        # Hash password
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
        
        # Create user
        user = await self.user_manager.create_user({
            "email": email,
            "password": hashed.decode(),
            "fullname": fullname,
            "created_at": datetime.utcnow()
        })
        
        # Generate tokens
        access_token = self._create_token(user["id"], "access")
        refresh_token = self._create_token(user["id"], "refresh")
        
        return {
            "user": {**user, "password": None},
            "access_token": access_token,
            "refresh_token": refresh_token
        }
        
    async def login(self, email: str, password: str) -> Dict[str, Any]:
        """Login user"""
        # Get user
        user = await self.user_manager.get_user_by_email(email)
        if not user:
            return {"error": "Email hoặc mật khẩu không đúng"}
            
        # Verify password
        if not bcrypt.checkpw(password.encode(), user["password"].encode()):
            return {"error": "Email hoặc mật khẩu không đúng"}
            
        # Generate tokens
        access_token = self._create_token(user["id"], "access")
        refresh_token = self._create_token(user["id"], "refresh")
        
        return {
            "user": {**user, "password": None},
            "access_token": access_token,
            "refresh_token": refresh_token
        }
        
    def _create_token(self, user_id: str, token_type: str = "access") -> str:
        """Create JWT token"""
        expires_delta = timedelta(
            minutes=self.token_expire_minutes if token_type == "access" else self.token_expire_minutes * 24
        )
        
        to_encode = {
            "sub": str(user_id),
            "type": token_type,
            "exp": datetime.utcnow() + expires_delta
        }
        
        return jwt.encode(to_encode, self.secret_key, algorithm="HS256")
        
    async def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            user_id = payload["sub"]
            token_type = payload["type"]
            
            # Get user
            user = await self.user_manager.get_user_by_id(user_id)
            if not user:
                return None
                
            return {**user, "token_type": token_type}
            
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None