from flask import Blueprint, request, jsonify, current_app
from modules.supabase_service import supabase_service

users_bp = Blueprint('users', __name__, url_prefix='/api')

@users_bp.route('/users', methods=['GET'])
def get_all_users():
    """List all users from Supabase"""
    try:
        # Fetch all users from 'users' table
        users = supabase_service.query_records('users', select='*')
        return jsonify(users), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@users_bp.route('/users/<user_id>', methods=['GET'])
def get_user_by_id(user_id):
    """Get specific user details from Supabase"""
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400

    try:
        # Query 'users' table where id equals user_id
        # Note: query_records returns a list
        users = supabase_service.query_records('users', select='*', filters={'id': user_id})
        
        if not users:
            return jsonify({"error": "User not found"}), 404
            
        return jsonify(users[0]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
