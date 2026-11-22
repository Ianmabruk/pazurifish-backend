import os
import secrets

from flask import Blueprint, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.models import AdminUser

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')
ADMIN_TOKENS = {}

DEFAULT_ADMIN_EMAILS = {
    'ian@gmail.com',
    'noa@pasuri@gmail.com',
    'dixon@pasuri@gmail.com',
}


def get_allowed_admin_emails():
    configured = os.getenv('ADMIN_ALLOWED_EMAILS', '')
    emails = {item.strip().lower() for item in configured.split(',') if item.strip()}
    return emails or DEFAULT_ADMIN_EMAILS


def normalize_admin_email(email):
    return str(email or '').strip().lower()


def get_authenticated_admin():
    header = request.headers.get('Authorization', '')
    if not header.startswith('Bearer '):
        return None
    token = header.split(' ', 1)[1].strip()
    email = ADMIN_TOKENS.get(token)
    if not email:
        return None
    email = normalize_admin_email(email)
    if email not in get_allowed_admin_emails():
        return None
    return AdminUser.query.filter_by(email=email).first()


@auth_bp.post('/register')
def register_user():
    payload = request.get_json(silent=True) or {}
    name = payload.get('full_name') or payload.get('name')
    email = normalize_admin_email(payload.get('email'))
    password = payload.get('password')

    if not all([name, email, password]):
        return jsonify({'error': 'full_name, email and password are required'}), 400
    if email not in get_allowed_admin_emails():
        return jsonify({'error': 'This email is not authorized for administrator access.'}), 403

    if AdminUser.query.filter_by(email=email).first():
        return jsonify({'error': 'An admin account with that email already exists.'}), 409

    db.session.add(AdminUser(
        email=email,
        full_name=name,
        role='administrator',
        password_hash=generate_password_hash(password),
    ))
    db.session.commit()
    return jsonify({'message': 'User registered successfully.'}), 201


@auth_bp.post('/login')
def login_user():
    payload = request.get_json(silent=True) or {}
    email = normalize_admin_email(payload.get('email'))
    password = payload.get('password') or ''

    if not all([email, password]):
        return jsonify({'error': 'email and password are required'}), 400
    if email not in get_allowed_admin_emails():
        return jsonify({'error': 'This email is not authorized for administrator access.'}), 403

    user = AdminUser.query.filter_by(email=email).first()
    if user is None or not check_password_hash(user.password_hash, password):
        return jsonify({'error': 'Invalid credentials'}), 401

    token = secrets.token_urlsafe(32)
    ADMIN_TOKENS[token] = email
    return jsonify({'message': 'Login successful.', 'token': token, 'user': user.to_dict()}), 200


@auth_bp.post('/provision-admin')
def provision_admin():
    provision_token = os.getenv('ADMIN_PROVISION_TOKEN', '')
    supplied_token = str(request.headers.get('X-Admin-Provision-Token') or '').strip()
    if not provision_token or supplied_token != provision_token:
        return jsonify({'error': 'Administrator provisioning is not authorized.'}), 403

    payload = request.get_json(silent=True) or {}
    email = normalize_admin_email(payload.get('email'))
    password = payload.get('password') or ''
    full_name = str(payload.get('full_name') or 'Pazuri Administrator').strip()
    if email not in get_allowed_admin_emails():
        return jsonify({'error': 'This email is not authorized for administrator access.'}), 403
    if len(password) < 8:
        return jsonify({'error': 'Password must contain at least 8 characters.'}), 400

    user = AdminUser.query.filter_by(email=email).first()
    if user:
        user.full_name = full_name
        user.password_hash = generate_password_hash(password)
    else:
        db.session.add(AdminUser(
            email=email,
            full_name=full_name,
            role='administrator',
            password_hash=generate_password_hash(password),
        ))
    db.session.commit()
    return jsonify({'message': 'Administrator account provisioned securely.'}), 201


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


@auth_bp.post('/password')
def change_password():
    user = get_authenticated_admin()
    if user is None:
        return jsonify({'error': 'Unauthorized'}), 401
    payload = request.get_json(silent=True) or {}
    current_password = payload.get('current_password', '')
    new_password = payload.get('new_password', '')
    if not check_password_hash(user.password_hash, current_password):
        return jsonify({'error': 'Current password is incorrect.'}), 400
    if len(new_password) < 8:
        return jsonify({'error': 'New password must be at least 8 characters.'}), 400
    user.password_hash = generate_password_hash(new_password)
    db.session.commit()
    return jsonify({'message': 'Password changed successfully.'})
