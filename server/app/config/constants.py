from enum import Enum

class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"

class ErrorCodes(str, Enum):
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    USER_EXISTS = "USER_EXISTS"
    INVALID_TOKEN = "INVALID_TOKEN"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    USER_LOCKED = "USER_LOCKED"

API_RESPONSES = {
    "AUTH": {
        "LOGIN_SUCCESS": "Đăng nhập thành công",
        "REGISTER_SUCCESS": "Đăng ký thành công",
        "INVALID_CREDENTIALS": "Email hoặc mật khẩu không đúng",
        "USER_EXISTS": "Email đã được đăng ký",
        "ACCOUNT_LOCKED": "Tài khoản đã bị khóa"
    }
}