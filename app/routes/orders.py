from datetime import datetime

from flask import Blueprint, jsonify, request

from app.extensions import db
from app.models import Order, OrderItem, Product

orders_bp = Blueprint('orders', __name__, url_prefix='/api')


@orders_bp.post('/orders')
def create_order():
    payload = request.get_json(silent=True) or {}
    items = payload.get('items', [])
    delivery_area = payload.get('delivery_area') or 'Nairobi'
    customer = payload.get('customer', {})
    if not items:
        return jsonify({'error': 'Order must include at least one item.'}), 400

    subtotal = 0.0
    order_items = []
    for item in items:
        product_id = item.get('product_id')
        product = Product.query.get(product_id) if product_id else None
        if product is None:
            product = Product.query.filter_by(name=item.get('name', '')).first()
        if product is None:
            return jsonify({'error': f"Product not found: {item.get('name', 'unknown')}"}), 400
        quantity = int(item.get('quantity', 0) or 0)
        if quantity <= 0:
            return jsonify({'error': 'Item quantity must be greater than zero.'}), 400
        unit_price = float(item.get('price', product.selling_price or product.price))
        total_for_item = unit_price * quantity
        subtotal += total_for_item
        order_items.append({
            'product_id': product.id,
            'product_name': product.name,
            'quantity': quantity,
            'unit_price': unit_price,
            'total_price': total_for_item,
        })

    order_number = f"PF-{datetime.utcnow().strftime('%Y')}-{len(Order.query.all()) + 1:04d}"
    order = Order(
        order_number=order_number,
        customer_name=(customer or {}).get('name') or 'Walk-in customer',
        customer_phone=(customer or {}).get('phone') or 'Not provided',
        delivery_area=delivery_area,
        delivery_address=(customer or {}).get('address') or '',
        source='ONLINE',
        subtotal=subtotal,
        discount=0.0,
        delivery_fee=0.0,
        total=subtotal,
        order_status='PENDING_CONFIRMATION',
        payment_status='PENDING',
        whatsapp_status='PENDING',
    )
    db.session.add(order)
    db.session.flush()
    for item in order_items:
        db.session.add(OrderItem(
            order_id=order.id,
            product_id=item['product_id'],
            product_name=item['product_name'],
            quantity=item['quantity'],
            unit_price=item['unit_price'],
            total_price=item['total_price'],
        ))
    db.session.commit()
    return jsonify({'order': order.to_dict()}), 201


@orders_bp.get('/orders')
def list_orders():
    orders = [order.to_dict() for order in Order.query.order_by(Order.created_at.desc()).all()]
    return jsonify({'orders': orders})
