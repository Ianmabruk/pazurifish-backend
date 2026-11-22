from flask import Blueprint, jsonify, request
from sqlalchemy import func

from app.extensions import db
from app.models import Category
from app.routes.auth import get_authenticated_admin

categories_bp = Blueprint('categories', __name__, url_prefix='/api')


@categories_bp.get('/categories')
def list_categories():
    categories = Category.query.filter_by(is_active=True).order_by(Category.display_order.asc(), Category.id.asc()).all()
    return jsonify({'categories': [category.to_dict() for category in categories]})


@categories_bp.get('/categories/homepage')
def homepage_categories():
    categories = Category.query.filter_by(is_active=True, show_on_homepage=True).order_by(Category.display_order.asc(), Category.id.asc()).all()
    return jsonify({'categories': [category.to_dict() for category in categories]})


@categories_bp.route('/admin/categories', methods=['GET', 'POST'])
def manage_categories():
    if get_authenticated_admin() is None:
        return jsonify({'error': 'Unauthorized'}), 401

    if request.method == 'POST':
        payload = request.get_json(silent=True) or {}
        name = str(payload.get('name', '')).strip()
        if not name:
            return jsonify({'error': 'Category name is required.'}), 400
        if Category.query.filter(func.lower(Category.name) == name.lower()).first():
            return jsonify({'error': 'Category already exists.'}), 400
        category = Category(
            name=name,
            image_url=payload.get('image_url', ''),
            display_order=int(payload.get('display_order', 0) or 0),
            is_active=bool(payload.get('is_active', True)),
            show_on_homepage=bool(payload.get('show_on_homepage', True)),
        )
        db.session.add(category)
        db.session.commit()
        return jsonify({'category': category.to_dict()}), 201

    categories = Category.query.order_by(Category.display_order.asc(), Category.id.asc()).all()
    return jsonify({'categories': [category.to_dict() for category in categories]})


@categories_bp.route('/admin/categories/<int:category_id>', methods=['PUT', 'DELETE'])
def manage_category(category_id):
    if get_authenticated_admin() is None:
        return jsonify({'error': 'Unauthorized'}), 401

    category = Category.query.get_or_404(category_id)
    if request.method == 'DELETE':
        db.session.delete(category)
        db.session.commit()
        return jsonify({'deleted': True, 'id': category_id})

    payload = request.get_json(silent=True) or {}
    if 'name' in payload:
        name = str(payload['name']).strip()
        if not name:
            return jsonify({'error': 'Category name is required.'}), 400
        duplicate = Category.query.filter(func.lower(Category.name) == name.lower(), Category.id != category_id).first()
        if duplicate:
            return jsonify({'error': 'Category already exists.'}), 400
        category.name = name
    if 'image_url' in payload:
        category.image_url = payload['image_url']
    if 'display_order' in payload:
        category.display_order = int(payload['display_order'] or 0)
    if 'is_active' in payload:
        category.is_active = bool(payload['is_active'])
    if 'show_on_homepage' in payload:
        category.show_on_homepage = bool(payload['show_on_homepage'])
    db.session.commit()
    return jsonify({'category': category.to_dict()})
