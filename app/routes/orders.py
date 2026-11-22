from datetime import datetime

from flask import Blueprint, jsonify, request

from app.extensions import db

from app.extensions import db
from app.models import Order, OrderItem, OrderStatusUpdate, Product, Sale, SaleItem, StockMovement

orders_bp = Blueprint('orders', __name__, url_prefix='/api')


def next_order_number():
    count = Order.query.count() + 1
    return f"PF-{datetime.utcnow().strftime('%Y%m%d')}-{count:05d}"


def next_tracking_number():
    count = Order.query.count() + 1
    return f"PAZ-{datetime.utcnow().strftime('%Y%m%d')}-{count:06d}"


def next_receipt_number():
    count = Sale.query.count() + 1
    return f"POS-{datetime.utcnow().strftime('%Y%m%d')}-{count:05d}"


@orders_bp.post('/orders')
def create_order():
    payload = request.get_json(silent=True) or {}
    items = payload.get('items', [])
    customer = payload.get('customer', {}) or {}
    if not items:
        return jsonify({'error': 'Order must include at least one item.'}), 400

    idempotency_key = str(payload.get('idempotency_key') or '').strip()
    if idempotency_key:
        existing = Order.query.filter_by(idempotency_key=idempotency_key).first()
        if existing:
            return jsonify({'order': existing.to_dict(), 'duplicate': True}), 200

    name = str(customer.get('name') or customer.get('full_name') or '').strip()
    phone = str(customer.get('phone') or customer.get('mobile') or '').strip()
    if not name or not phone:
        return jsonify({'error': 'Customer name and phone are required.'}), 400

    subtotal = 0.0
    prepared_items = []
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
        if not product.is_available:
            return jsonify({'error': f"{product.name} is currently unavailable."}), 400
        if quantity > product.stock_quantity:
            return jsonify({'error': f"Only {product.stock_quantity} units of {product.name} are available."}), 400
        unit_price = float(item.get('price', product.selling_price))
        line_total = unit_price * quantity
        subtotal += line_total
        prepared_items.append({
            'product': product,
            'quantity': quantity,
            'unit_price': unit_price,
            'line_total': line_total,
        })

    order = Order(
        order_number=next_order_number(),
        tracking_number=next_tracking_number(),
        idempotency_key=idempotency_key or None,
        customer_name=name,
        customer_phone=phone,
        delivery_area=str(payload.get('delivery_area') or customer.get('location') or 'Nairobi'),
        delivery_address=str(customer.get('address') or customer.get('delivery_address') or ''),
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
    db.session.add(OrderStatusUpdate(
        order_id=order.id,
        status='PENDING_CONFIRMATION',
        note='Order received',
    ))

    for item in prepared_items:
        product = item['product']
        db.session.add(OrderItem(
            order_id=order.id,
            product_id=product.id,
            product_name=product.name,
            quantity=item['quantity'],
            unit_price=item['unit_price'],
            total_price=item['line_total'],
        ))
        before_stock = product.stock_quantity
        product.stock_quantity = max(0, before_stock - item['quantity'])
        db.session.add(StockMovement(
            product_id=product.id,
            movement_type='sale',
            quantity_before=before_stock,
            quantity_changed=-item['quantity'],
            quantity_after=product.stock_quantity,
            reason='online-order',
            reference_type='order',
            reference_id=str(order.id),
            user_id='customer',
        ))

    db.session.commit()
    return jsonify({'order': Order.query.get(order.id).to_dict()}), 201


@orders_bp.post('/pos/sales')
def create_pos_sale():
    payload = request.get_json(silent=True) or {}
    items = payload.get('items', [])
    if not items:
        return jsonify({'error': 'Sale must include at least one item.'}), 400

    subtotal = 0.0
    prepared_items = []
    for item in items:
        product_id = item.get('product_id')
        product = Product.query.get(product_id) if product_id else None
        if product is None:
            return jsonify({'error': f"Product not found: {item.get('product_name', 'unknown')}"}), 400
        quantity = int(item.get('quantity', 0) or 0)
        if quantity <= 0:
            return jsonify({'error': 'Item quantity must be greater than zero.'}), 400
        if quantity > product.stock_quantity:
            return jsonify({'error': f"Only {product.stock_quantity} units of {product.name} are available."}), 400
        unit_price = float(item.get('price', product.selling_price))
        line_total = unit_price * quantity
        subtotal += line_total
        prepared_items.append({'product': product, 'quantity': quantity, 'unit_price': unit_price, 'line_total': line_total})

    sale = Sale(
        receipt_number=next_receipt_number(),
        cashier_id=str(payload.get('cashier_id') or 'cashier'),
        source='POS',
        subtotal=subtotal,
        discount=float(payload.get('discount', 0) or 0),
        total=float(payload.get('total', subtotal) or subtotal),
        payment_method=str(payload.get('payment_method') or 'Cash'),
        payment_reference=str(payload.get('payment_reference') or ''),
        sale_status='COMPLETED',
    )
    db.session.add(sale)
    db.session.flush()

    for item in prepared_items:
        product = item['product']
        db.session.add(SaleItem(
            sale_id=sale.id,
            product_id=product.id,
            product_name=product.name,
            quantity=item['quantity'],
            unit_price=item['unit_price'],
            total_price=item['line_total'],
        ))
        before_stock = product.stock_quantity
        product.stock_quantity = max(0, before_stock - item['quantity'])
        db.session.add(StockMovement(
            product_id=product.id,
            movement_type='sale',
            quantity_before=before_stock,
            quantity_changed=-item['quantity'],
            quantity_after=product.stock_quantity,
            reason='pos-sale',
            reference_type='sale',
            reference_id=str(sale.id),
            user_id=str(payload.get('cashier_id') or 'cashier'),
        ))

    db.session.commit()
    return jsonify({'sale': Sale.query.get(sale.id).to_dict()}), 201


@orders_bp.get('/orders')
def list_orders():
    orders = [order.to_dict() for order in Order.query.order_by(Order.created_at.desc()).all()]
    return jsonify({'orders': orders})


@orders_bp.get('/orders/tracking/<tracking_number>')
def track_order(tracking_number):
    normalized = tracking_number.strip().upper()
    order = Order.query.filter(
        db.func.upper(Order.tracking_number) == normalized
    ).first()
    if order is None:
        order = Order.query.filter(db.func.upper(Order.order_number) == normalized).first()
    if order is None:
        return jsonify({'error': 'No order was found for that tracking number.'}), 404

    return jsonify({'order': {
        'tracking_number': order.tracking_number or order.order_number,
        'order_number': order.order_number,
        'order_date': order.created_at.isoformat() if order.created_at else None,
        'status': order.order_status,
        'payment_status': order.payment_status,
        'total': float(order.total),
        'delivery_area': order.delivery_area,
        'items': [item.to_dict() for item in order.items],
        'status_history': [update.to_dict() for update in sorted(order.status_updates, key=lambda item: item.created_at or datetime.min)],
    }})


@orders_bp.get('/sales')
def list_sales():
    sales = [sale.to_dict() for sale in Sale.query.order_by(Sale.created_at.desc()).all()]
    return jsonify({'sales': sales})
