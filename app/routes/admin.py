from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request

from app.extensions import db
from app.models import Order, OrderItem, OrderStatusUpdate, Product, Sale, SaleItem, StockMovement
from app.routes.auth import get_authenticated_admin

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')


def require_admin():
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return False
    return get_authenticated_admin() is not None


@admin_bp.before_request
def guard_admin():
    if request.method == 'OPTIONS':
        return None
    if request.path.startswith('/api/admin/') and request.path not in {'/api/admin/content/hero'}:
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
    if 'payment_status' in payload:
        return jsonify({'error': 'Payment status must not be changed without a verified payment record.'}), 400
    db.session.add(OrderStatusUpdate(
        order_id=order.id,
        status=order.order_status,
        note=str(payload.get('note') or ''),
    ))
    db.session.commit()
    return jsonify({'order': order.to_dict()})


@admin_bp.delete('/orders/<int:order_id>')
def cancel_order(order_id):
    order = Order.query.get_or_404(order_id)
    order.order_status = 'CANCELLED'
    order.payment_status = 'CANCELLED'
    db.session.commit()
    return jsonify({'deleted': True, 'order': order.to_dict()})


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


@admin_bp.get('/sales')
def admin_sales():
    sales = [sale.to_dict() for sale in Sale.query.order_by(Sale.created_at.desc()).all()]
    return jsonify({'sales': sales})


@admin_bp.get('/reports/sales')
def sales_report():
    completed_sales = Sale.query.filter_by(sale_status='COMPLETED').all()
    completed_orders = Order.query.filter(Order.order_status.notin_(['CANCELLED', 'PENDING_CONFIRMATION', 'PENDING'])).all()
    now = datetime.utcnow()
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = day_start - timedelta(days=(day_start.weekday() + 1) % 7)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    total_online = sum(float(order.total) for order in completed_orders)
    total_pos = sum(float(sale.total) for sale in completed_sales)
    best_selling = {}
    for item in OrderItem.query.all():
        best_selling[item.product_name] = best_selling.get(item.product_name, 0) + item.quantity
    for item in SaleItem.query.all():
        best_selling[item.product_name] = best_selling.get(item.product_name, 0) + item.quantity

    report = {
        'total_sales': total_online + total_pos,
        'total_online_orders': len(completed_orders),
        'total_pos_sales': len(completed_sales),
        'daily_sales': sum(float(sale.total) for sale in completed_sales if sale.created_at and sale.created_at >= day_start) + sum(float(order.total) for order in completed_orders if order.created_at and order.created_at >= day_start),
        'weekly_sales': sum(float(sale.total) for sale in completed_sales if sale.created_at and sale.created_at >= week_start) + sum(float(order.total) for order in completed_orders if order.created_at and order.created_at >= week_start),
        'monthly_sales': sum(float(sale.total) for sale in completed_sales if sale.created_at and sale.created_at >= month_start) + sum(float(order.total) for order in completed_orders if order.created_at and order.created_at >= month_start),
        'best_selling_products': sorted(best_selling.items(), key=lambda pair: pair[1], reverse=True)[:5],
        'current_stock_levels': {product.name: product.stock_quantity for product in Product.query.order_by(Product.name).all()},
        'total_products': Product.query.count(),
    }
    return jsonify({'report': report})


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
    cash = sum(float(sale.total) for sale in Sale.query.filter_by(payment_method='Cash').all())
    mpesa = sum(float(sale.total) for sale in Sale.query.filter_by(payment_method='M-Pesa').all())
    card = sum(float(sale.total) for sale in Sale.query.filter_by(payment_method='Card').all())
    return jsonify({'report': {'cash': cash, 'mpesa': mpesa, 'card': card, 'other': 0}})
