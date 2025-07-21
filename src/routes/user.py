from flask import Blueprint, jsonify

user_bp = Blueprint('user', __name__)

@user_bp.route('/users', methods=['GET'])
def get_users():
    # Placeholder response
    return jsonify({'users': []})
