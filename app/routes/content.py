from datetime import datetime

from flask import Blueprint, current_app, jsonify, request

from app.extensions import db
from app.models import HeroContent

content_bp = Blueprint('content', __name__, url_prefix='/api')


@content_bp.get('/content/hero')
def get_hero():
    hero = HeroContent.query.order_by(HeroContent.id.desc()).first()
    if not hero:
        hero = HeroContent(
            title='FRESH CATCH, DELIVERED EVERY DAY.',
            subtitle='FRESH FROM LAKE VICTORIA',
            image_url='https://images.unsplash.com/photo-1544943910-4c1dc44aab77?auto=format&fit=crop&w=1200&q=80',
        )
        db.session.add(hero)
        db.session.commit()
    return jsonify({'hero': hero.to_dict()})


@content_bp.route('/admin/content/hero', methods=['GET', 'PUT'])
def admin_hero():
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return jsonify({'error': 'Unauthorized'}), 401

    hero = HeroContent.query.order_by(HeroContent.id.desc()).first()
    if not hero:
        hero = HeroContent()
        db.session.add(hero)

    if request.method == 'PUT':
        payload = request.get_json(silent=True) or {}
        hero.title = payload.get('title', hero.title)
        hero.subtitle = payload.get('subtitle', hero.subtitle)
        hero.image_url = payload.get('image_url', hero.image_url)
        hero.is_published = payload.get('is_published', hero.is_published)
        hero.updated_at = datetime.utcnow()
        db.session.commit()

    return jsonify({'hero': hero.to_dict()})


@content_bp.post('/admin/uploads/hero')
def upload_hero_image():
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return jsonify({'error': 'Unauthorized'}), 401

    payload = request.get_json(silent=True) or {}
    image_url = payload.get('image_url') or payload.get('url')
    if not image_url:
        return jsonify({'error': 'image_url is required'}), 400

    hero = HeroContent.query.order_by(HeroContent.id.desc()).first() or HeroContent()
    hero.image_url = image_url
    hero.updated_at = datetime.utcnow()
    db.session.add(hero)
    db.session.commit()

    return jsonify({'hero': hero.to_dict()})
