from flask import Blueprint, jsonify, request

from app.extensions import db
from app.models import Product

products_bp = Blueprint('products', __name__, url_prefix='/api')


@products_bp.get('/products')
def get_products():
    products = [product.to_dict() for product in Product.query.order_by(Product.name.asc()).all()]
    return jsonify({'products': products})


@products_bp.get('/products/<int:product_id>')
def get_product(product_id):
    product = Product.query.get_or_404(product_id)
    return jsonify({'product': product.to_dict()})


@products_bp.post('/products')
def create_product():
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
        image_url=payload.get('image_url', ''),
        stock_quantity=int(payload.get('stock_quantity', 0) or 0),
        minimum_stock=int(payload.get('minimum_stock', 0) or 0),
        is_available=bool(payload.get('is_available', True)),
    )
    db.session.add(product)
    db.session.commit()
    return jsonify({'product': product.to_dict()}), 201
