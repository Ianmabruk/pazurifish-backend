from flask import Blueprint, jsonify, request

from app.extensions import db
from app.models import Product
from app.routes.auth import get_authenticated_admin

products_bp = Blueprint('products', __name__, url_prefix='/api')


@products_bp.get('/products')
def get_products():
    products = [product.to_dict() for product in Product.query.filter_by(is_available=True).order_by(Product.name.asc()).all()]
    return jsonify({'products': products})


@products_bp.get('/products/<int:product_id>')
def get_product(product_id):
    product = Product.query.get_or_404(product_id)
    return jsonify({'product': product.to_dict()})


@products_bp.post('/products')
def create_product():
    auth_user = get_authenticated_admin()
    if auth_user is None:
        return jsonify({'error': 'Unauthorized'}), 401

    payload = request.get_json(silent=True) or {}
    required = {'name', 'description', 'category', 'selling_price', 'unit'}
    missing = sorted(required.difference(payload.keys()))

    if missing:
        return jsonify({'error': f'Missing required fields: {missing}'}), 400

    product = Product(
        sku=payload.get('sku') or f"PF-{Product.query.count() + 1:04d}",
        name=payload['name'],
        description=payload['description'],
        specifications=payload.get('specifications', ''),
        category=payload['category'],
        selling_price=float(payload['selling_price']),
        cost_price=float(payload.get('cost_price', 0) or 0),
        unit=payload['unit'],
        image_url=payload.get('image_url') or payload.get('image') or '',
        stock_quantity=int(payload.get('stock_quantity', 0) or 0),
        minimum_stock=int(payload.get('minimum_stock', 0) or 0),
        is_available=bool(payload.get('is_available', True)),
    )
    db.session.add(product)
    db.session.commit()
    return jsonify({'product': product.to_dict()}), 201


@products_bp.route('/products/<int:product_id>', methods=['PUT', 'DELETE'])
def manage_product(product_id):
    admin = get_authenticated_admin()
    if admin is None:
        return jsonify({'error': 'Unauthorized'}), 401

    product = Product.query.get_or_404(product_id)
    if request.method == 'DELETE':
        db.session.delete(product)
        db.session.commit()
        return jsonify({'deleted': True, 'id': product_id})

    payload = request.get_json(silent=True) or {}
    product.name = payload.get('name', product.name)
    product.description = payload.get('description', product.description)
    product.specifications = payload.get('specifications', product.specifications)
    product.category = payload.get('category', product.category)
    product.selling_price = float(payload.get('selling_price', product.selling_price) or product.selling_price)
    product.cost_price = float(payload.get('cost_price', product.cost_price) or product.cost_price)
    product.unit = payload.get('unit', product.unit)
    product.image_url = payload.get('image_url') or payload.get('image') or product.image_url
    product.stock_quantity = int(payload.get('stock_quantity', product.stock_quantity) or product.stock_quantity)
    product.minimum_stock = int(payload.get('minimum_stock', product.minimum_stock) or product.minimum_stock)
    product.is_available = bool(payload.get('is_available', product.is_available))
    product.sku = payload.get('sku', product.sku)
    db.session.commit()
    return jsonify({'product': product.to_dict()})


@products_bp.get('/admin/products')
def admin_products():
    admin = get_authenticated_admin()
    if admin is None:
        return jsonify({'error': 'Unauthorized'}), 401
    products = [product.to_dict() for product in Product.query.order_by(Product.name.asc()).all()]
    return jsonify({'products': products})
