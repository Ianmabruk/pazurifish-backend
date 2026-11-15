from flask import Blueprint, jsonify, request

from app.extensions import db
from app.models import Order, WhatsAppMessage

whatsapp_bp = Blueprint('whatsapp', __name__, url_prefix='/api/whatsapp')


@whatsapp_bp.get('/webhook')
def verify_webhook():
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    if mode == 'subscribe' and token == 'pazuri-whatsapp-verify':
        return challenge, 200
    return jsonify({'error': 'Verification failed'}), 403


@whatsapp_bp.post('/webhook')
def handle_webhook():
    payload = request.get_json(silent=True) or {}
    entries = payload.get('entry', [])
    for entry in entries:
        for change in entry.get('changes', []):
            value = change.get('value', {})
            messages = value.get('messages', [])
            for message in messages:
                message_id = message.get('id') or 'unknown'
                recipient = value.get('metadata', {}).get('display_phone_number')
                msg = WhatsAppMessage(
                    message_id=message_id,
                    recipient=recipient,
                    message_type=message.get('type', 'text'),
                    delivery_status='received',
                )
                db.session.add(msg)
                db.session.commit()
    return jsonify({'status': 'received'})


@whatsapp_bp.get('/messages')
def list_messages():
    records = [message.to_dict() for message in WhatsAppMessage.query.order_by(WhatsAppMessage.created_at.desc()).all()]
    return jsonify({'messages': records})


@whatsapp_bp.post('/send-order')
def send_order_message():
    payload = request.get_json(silent=True) or {}
    order_id = payload.get('order_id')
    order = Order.query.get(order_id)
    if not order:
        return jsonify({'error': 'Invalid order'}), 404

    message_text = (
        f"PAZURI FISH — NEW ORDER\n\n"
        f"Order Number: {order.order_number}\n"
        f"Customer: {order.customer_name}\n"
        f"Phone: {order.customer_phone}\n"
        f"Delivery Area: {order.delivery_area}\n"
        f"Products: {', '.join(item.product_name for item in order.items)}\n"
        f"Subtotal: KES {order.subtotal}\n\n"
        f"Order Status: {order.order_status}. Please confirm product availability and delivery charges."
    )
    return jsonify({'status': 'queued', 'message': message_text, 'order_id': order.id})
