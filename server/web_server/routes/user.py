from flask import Blueprint

bp = Blueprint('user', __name__, url_prefix='/user')

@bp.route('/')
def user_index():
    return "User API placeholder"
