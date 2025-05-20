# server/web_server/routes/navigation.py
from flask import Blueprint, jsonify
import os
import json

bp = Blueprint('navigation', __name__)

@bp.route('/api/flow/<domain>', methods=['GET'])
def get_flow(domain):
    file_path = os.path.join(os.path.dirname(__file__), f'../../domains/{domain}/interaction_flow.json')
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return jsonify(data)
    except FileNotFoundError:
        return jsonify({"error": "Không tìm thấy file flow"}), 404
