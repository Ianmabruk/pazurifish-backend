from datetime import datetime
import os
import uuid

from flask import Blueprint, current_app, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import HeroContent
from app.routes.auth import get_authenticated_admin

content_bp = Blueprint('content', __name__, url_prefix='/api')

ALLOWED_IMAGE_TYPES = {'png', 'jpg', 'jpeg', 'webp', 'gif'}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024


@content_bp.post('/admin/uploads')
def upload_image():
    admin = get_authenticated_admin()
    if admin is None:
        return jsonify({'error': 'Unauthorized'}), 401
    image = request.files.get('file') or request.files.get('image')
    if image is None:
        return jsonify({'error': 'An image file is required.'}), 400
    filename = secure_filename(image.filename or '')
    extension = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if extension not in ALLOWED_IMAGE_TYPES:
        return jsonify({'error': 'Unsupported image type.'}), 400
    image.seek(0, os.SEEK_END)
    size = image.tell()
    image.seek(0)
    if size > MAX_UPLOAD_BYTES:
        return jsonify({'error': 'Image must be 5 MB or smaller.'}), 400

    upload_folder = os.path.join(current_app.instance_path, 'uploads')
    os.makedirs(upload_folder, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}.{extension}"
    image.save(os.path.join(upload_folder, stored_name))
    public_url = f"{request.host_url.rstrip('/')}/api/uploads/{stored_name}"
    return jsonify({'image_url': public_url, 'url': public_url}), 201


@content_bp.get('/uploads/<path:filename>')
def serve_upload(filename):
    return send_from_directory(os.path.join(current_app.instance_path, 'uploads'), filename)


@content_bp.get('/content/hero')
def get_hero():
    slides = HeroContent.query.filter(HeroContent.is_published.is_(True)).order_by(HeroContent.sort_order.asc(), HeroContent.id.asc()).all()
    fixed_images = [
        '/images/products/fresh-fish.jpg',
        '/images/categories/combos/family-feast.jpg',
        '/images/categories/kitchen/grilled-tilapia.jpg',
        '/images/categories/drinks/tropical-cooler.jpg',
        '/images/products/fish-cuts.jpg',
        '/images/products/fish-and-chips.jpg',
    ]
    existing_images = {slide.image_url for slide in slides}
    for sort_order, image_url in enumerate(fixed_images):
        if image_url in existing_images:
            continue
        db.session.add(HeroContent(
            title='Pazuri Fish Fresh Catch',
            subtitle='FRESH FROM LAKE VICTORIA',
            description="Sourced from Lake Victoria's waters",
            image_url=image_url,
            sort_order=sort_order,
            is_published=True,
        ))
    if slides:
        db.session.commit()
        slides = HeroContent.query.filter(HeroContent.is_published.is_(True)).order_by(HeroContent.sort_order.asc(), HeroContent.id.asc()).all()
    else:
        db.session.commit()
        slides = HeroContent.query.filter(HeroContent.is_published.is_(True)).order_by(HeroContent.sort_order.asc(), HeroContent.id.asc()).all()
    slides = slides[:6]
    return jsonify({'hero': slides[0].to_dict(), 'slides': [slide.to_dict() for slide in slides]})


@content_bp.route('/admin/content/hero', methods=['GET', 'POST', 'PUT', 'DELETE'])
def admin_hero():
    admin = get_authenticated_admin()
    if admin is None:
        return jsonify({'error': 'Unauthorized'}), 401

    if request.method == 'GET':
        slides = HeroContent.query.order_by(HeroContent.sort_order.asc(), HeroContent.id.asc()).all()
        return jsonify({'slides': [slide.to_dict() for slide in slides]})

    if request.method == 'POST':
        payload = request.get_json(silent=True) or {}
        slide = HeroContent(
            title=payload.get('title', 'FRESH CATCH, DELIVERED EVERY DAY.'),
            subtitle=payload.get('subtitle', 'FRESH FROM LAKE VICTORIA'),
            description=payload.get('description', ''),
            cta_label=payload.get('cta_label', ''),
            cta_url=payload.get('cta_url', ''),
            image_url=payload.get('image_url') or payload.get('url') or 'https://images.unsplash.com/photo-1544943910-4c1dc44aab77?auto=format&fit=crop&w=1200&q=80',
            sort_order=int(payload.get('sort_order', 0) or 0),
            is_published=bool(payload.get('is_published', True)),
        )
        db.session.add(slide)
        db.session.commit()
        return jsonify({'slide': slide.to_dict()}), 201

    if request.method == 'DELETE':
        payload = request.get_json(silent=True) or {}
        slide_id = payload.get('id') or request.args.get('id')
        if slide_id is None:
            return jsonify({'error': 'slide id is required'}), 400
        slide = HeroContent.query.get_or_404(int(slide_id))
        db.session.delete(slide)
        db.session.commit()
        return jsonify({'deleted': True, 'id': int(slide_id)})

    payload = request.get_json(silent=True) or {}
    slide_id = payload.get('id')
    if slide_id is None:
        return jsonify({'error': 'slide id is required'}), 400
    slide = HeroContent.query.get_or_404(int(slide_id))
    slide.title = payload.get('title', slide.title)
    slide.subtitle = payload.get('subtitle', slide.subtitle)
    slide.description = payload.get('description', slide.description)
    slide.cta_label = payload.get('cta_label', slide.cta_label)
    slide.cta_url = payload.get('cta_url', slide.cta_url)
    slide.image_url = payload.get('image_url') or payload.get('url') or slide.image_url
    slide.sort_order = int(payload.get('sort_order', slide.sort_order) or slide.sort_order)
    slide.is_published = payload.get('is_published', slide.is_published)
    slide.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'slide': slide.to_dict()})


@content_bp.post('/admin/uploads/hero')
def upload_hero_image():
    admin = get_authenticated_admin()
    if admin is None:
        return jsonify({'error': 'Unauthorized'}), 401

    payload = request.get_json(silent=True) or {}
    image_url = payload.get('image_url') or payload.get('url')
    if not image_url:
        return jsonify({'error': 'image_url is required'}), 400

    slide = HeroContent(
        title=payload.get('title', 'FRESH CATCH, DELIVERED EVERY DAY.'),
        subtitle=payload.get('subtitle', 'FRESH FROM LAKE VICTORIA'),
        image_url=image_url,
        sort_order=int(payload.get('sort_order', 0) or 0),
        is_published=bool(payload.get('is_published', True)),
    )
    db.session.add(slide)
    db.session.commit()
    return jsonify({'slide': slide.to_dict()}), 201
