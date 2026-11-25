from flask import Blueprint, jsonify, request

from app.extensions import db
from app.models import AdminSetting
from app.routes.auth import get_authenticated_admin


settings_bp = Blueprint('settings', __name__, url_prefix='/api')

DEFAULT_SETTINGS = {
    'business_name': 'Pazuri Fish',
    'contact_phone': '',
    'contact_email': '',
    'business_location': '',
    'delivery_information': '',
    'opening_hours': '',
    'website_announcement': '',
    'social_media': '{}',
    'currency': 'KES',
    'delivery_fee': '0',
}


def settings_dict():
    values = {setting.key: setting.value for setting in AdminSetting.query.all()}
    return {key: values.get(key, default) for key, default in DEFAULT_SETTINGS.items()}


@settings_bp.get('/settings')
def public_settings():
    return jsonify({'settings': settings_dict()})


@settings_bp.route('/admin/settings', methods=['GET', 'PUT'])
def manage_settings():
    if get_authenticated_admin() is None:
        return jsonify({'error': 'Unauthorized'}), 401

    if request.method == 'PUT':
        payload = request.get_json(silent=True) or {}
        allowed = set(DEFAULT_SETTINGS)
        unknown = set(payload).difference(allowed)
        if unknown:
            return jsonify({'error': f"Unsupported settings: {sorted(unknown)}"}), 400
        for key, value in payload.items():
            setting = AdminSetting.query.filter_by(key=key).first()
            if setting is None:
                setting = AdminSetting(key=key)
                db.session.add(setting)
            setting.value = str(value)
        db.session.commit()
    return jsonify({'settings': settings_dict()})
