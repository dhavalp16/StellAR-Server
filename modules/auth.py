from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from modules.models import db, User
import datetime

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    
    username = data.get('username')
    password = data.get('password')
    role = data.get('role', 'student')
    
    if not username or not password:
        return jsonify({"msg": "Missing username or password"}), 400
        
    if User.query.filter_by(username=username).first():
        return jsonify({"msg": "Username already exists"}), 400
        
    hashed_password = generate_password_hash(password)
    new_user = User(username=username, password_hash=hashed_password, role=role)
    
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({"msg": "User created successfully"}), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    
    username = data.get('username')
    password = data.get('password')
    
    user = User.query.filter_by(username=username).first()
    
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"msg": "Bad username or password"}), 401
        
    access_token = create_access_token(identity=str(user.id), expires_delta=datetime.timedelta(days=7))
    return jsonify(access_token=access_token, role=user.role, username=user.username), 200

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user_info():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    return jsonify({
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "xp": user.xp,
        "level": user.level
    }), 200
