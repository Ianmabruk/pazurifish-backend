from datetime import datetime

from flask import Blueprint, jsonify, request

from app.extensions import db
from app.models import Order, Product, Sale, StockMovement

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')


def require_admin():
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return False
    return True


@admin_bp.before_request
def guard_admin():
    if request.method == 'OPTIONS':
        return None
    if request.path in {'/api/admin/orders', '/api/admin/inventory', '/api/admin/inventory/adjustments', '/api/admin/inventory/movements', '/api/admin/inventory/low-stock', '/api/admin/reports/sales', '/api/admin/reports/inventory', '/api/admin/reports/products', '/api/admin/reports/payment-methods'}:
        if not require_admin():
            return jsonify({'error': 'Unauthorized'}), 401


@admin_bp.get('/orders')
def admin_orders():
    orders = [order.to_dict() for order in Order.query.order_by(Order.created_at.desc()).all()]
    return jsonify({'orders': orders})


@admin_bp.put('/orders/<int:order_id>/status')
def update_order_status(order_id):
    order = Order.query.get_or_404(order_id)
    payload = request.get_json(silent=True) or {}
    order.order_status = payload.get('status', order.order_status)
    order.whatsapp_status = payload.get('whatsapp_status', order.whatsapp_status)
    db.session.commit()
    return jsonify({'order': order.to_dict()})


@admin_bp.get('/inventory')
def list_inventory():
    products = [product.to_dict() for product in Product.query.order_by(Product.name).all()]
    return jsonify({'products': products})


@admin_bp.post('/inventory/adjustments')
def adjust_inventory():
    payload = request.get_json(silent=True) or {}
    product_id = payload.get('product_id')
    quantity_change = int(payload.get('quantity_change', 0))
    reason = payload.get('reason', 'manual-adjustment')
    product = Product.query.get_or_404(product_id)
    before = product.stock_quantity
    product.stock_quantity += quantity_change
    product.stock_quantity = max(0, product.stock_quantity)
    product.updated_at = datetime.utcnow()
    movement = StockMovement(
        product_id=product.id,
        movement_type='adjustment' if quantity_change >= 0 else 'removal',
        quantity_before=before,
        quantity_changed=quantity_change,
        quantity_after=product.stock_quantity,
        reason=reason,
        reference_type='inventory-adjustment',
        reference_id=str(product.id),
        user_id='admin',
    )
    db.session.add(movement)
    db.session.commit()
    return jsonify({'product': product.to_dict(), 'movement': {
        'product_id': product.id,
        'quantity_changed': quantity_change,
        'quantity_after': product.stock_quantity,
    }})


@admin_bp.get('/inventory/movements')
def inventory_movements():
    movements = []
    for movement in StockMovement.query.order_by(StockMovement.created_at.desc()).all():
        movements.append({
            'id': movement.id,
            'product_id': movement.product_id,
            'movement_type': movement.movement_type,
            'quantity_before': movement.quantity_before,
            'quantity_changed': movement.quantity_changed,
            'quantity_after': movement.quantity_after,
            'reason': movement.reason,
            'created_at': movement.created_at.isoformat() if movement.created_at else None,
        })
    return jsonify({'movements': movements})


@admin_bp.get('/inventory/low-stock')
def low_stock():
    products = [product.to_dict() for product in Product.query.filter(Product.stock_quantity <= Product.minimum_stock).all()]
    return jsonify({'products': products})


@admin_bp.get('/reports/sales')
def sales_report():
    totals = {
        'total_sales': sum(float(sale.total) for sale in Sale.query.all()),
        'total_orders': Order.query.count(),
        'total_products': Product.query.count(),
    }
    return jsonify({'report': totals})


@admin_bp.get('/reports/inventory')
def inventory_report():
    total_value = sum(float(product.selling_price * product.stock_quantity) for product in Product.query.all())
    return jsonify({'report': {'total_inventory_value': total_value}})


@admin_bp.get('/reports/products')
def product_report():
    products = [product.to_dict() for product in Product.query.all()]
    return jsonify({'products': products})


@admin_bp.get('/reports/payment-methods')
def payment_report():
    return jsonify({'report': {'cash': 0, 'mpesa': 0, 'card': 0, 'other': 0}})
