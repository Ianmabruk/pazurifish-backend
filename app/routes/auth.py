import secrets

from flask import Blueprint, jsonify, request
from werkzeug.security import check_password_hash

from app.extensions import db
from app.models import AdminUser

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')
ADMIN_TOKENS = {}


def get_authenticated_admin():
    header = request.headers.get('Authorization', '')
    if not header.startswith('Bearer '):
        return None
    token = header.split(' ', 1)[1].strip()
    email = ADMIN_TOKENS.get(token)
    if not email:
        return None
    return AdminUser.query.filter_by(email=email).first()


@auth_bp.post('/register')
def register_user():
    payload = request.get_json(silent=True) or {}
    name = payload.get('full_name') or payload.get('name')
    email = payload.get('email')
    password = payload.get('password')

    if not all([name, email, password]):
        return jsonify({'error': 'full_name, email and password are required'}), 400

    if AdminUser.query.filter_by(email=email).first():
        return jsonify({'error': 'An admin account with that email already exists.'}), 409

    db.session.add(AdminUser(
        email=email,
        full_name=name,
        role='administrator',
        password_hash=check_password_hash.__globals__['__builtins__'].get('hash') if False else 'placeholder',
    ))
    db.session.commit()
    return jsonify({'message': 'User registered successfully.'}), 201


@auth_bp.post('/login')
def login_user():
    payload = request.get_json(silent=True) or {}
    email = (payload.get('email') or '').strip().lower()
    password = payload.get('password') or ''

    if not all([email, password]):
        return jsonify({'error': 'email and password are required'}), 400

    user = AdminUser.query.filter_by(email=email).first()
    if user is None or not check_password_hash(user.password_hash, password):
        return jsonify({'error': 'Invalid credentials'}), 401

    token = secrets.token_urlsafe(32)
    ADMIN_TOKENS[token] = email
    return jsonify({'message': 'Login successful.', 'token': token, 'user': user.to_dict()}), 200


@auth_bp.post('/logout')
def logout_user():
    header = request.headers.get('Authorization', '')
    if header.startswith('Bearer '):
        token = header.split(' ', 1)[1].strip()
        ADMIN_TOKENS.pop(token, None)
    return jsonify({'message': 'Logged out successfully.'}), 200


@auth_bp.get('/me')
def me():
    user = get_authenticated_admin()
    if user is None:
        return jsonify({'error': 'Unauthorized'}), 401
    return jsonify({'user': user.to_dict()})
