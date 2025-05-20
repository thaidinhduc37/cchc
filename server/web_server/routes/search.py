from flask import Blueprint

bp = Blueprint('search', __name__, url_prefix='/search')

@bp.route('/')
def search_index():
    return "Search API placeholder"
