from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from functools import wraps
from flask import request, jsonify
import jwt

from app.config.app_config import Config 
from app.auth.auth_service import AuthService

config = Config()
auth_service = AuthService()

class JWTBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super(JWTBearer, self).__init__(auto_error=auto_error)
        self.auth_service = AuthService()

    async def __call__(self, request: Request) -> HTTPAuthorizationCredentials:
        credentials: HTTPAuthorizationCredentials = await super(JWTBearer, self).__call__(request)
        
        if not credentials:
            raise HTTPException(status_code=403, detail="Invalid authorization code")
            
        if not credentials.scheme == "Bearer":
            raise HTTPException(status_code=403, detail="Invalid authentication scheme")
            
        user = await self.auth_service.verify_token(credentials.credentials)
        if not user:
            raise HTTPException(status_code=403, detail="Invalid token or expired token")
            
        # Add user to request state
        request.state.user = user
        return credentials

def jwt_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Check if JWT is in headers
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({"error": "Token không hợp lệ"}), 401

        if not token:
            return jsonify({"error": "Không tìm thấy token"}), 401

        try:
            # Verify token
            payload = jwt.decode(token, config.JWT_SECRET_KEY, algorithms=["HS256"])
            request.user = auth_service.get_user_by_id(payload['sub'])

        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token hết hạn"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Token không hợp lệ"}), 401

        return f(*args, **kwargs)
    return decorated