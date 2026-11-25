from datetime import datetime
import json

from flask import Blueprint, jsonify, request

from app.extensions import db
from app.models import Deal, Product
from app.routes.auth import get_authenticated_admin


deals_bp = Blueprint('deals', __name__, url_prefix='/api')


def parse_datetime(value):
    if not value:
        return None
    parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    if parsed.tzinfo is not None:
        parsed = parsed.replace(tzinfo=None)
    return parsed


@deals_bp.get('/deals')
def public_deals():
    now = datetime.utcnow()
    deals = Deal.query.filter(
        Deal.is_active.is_(True),
        db.or_(Deal.start_date.is_(None), Deal.start_date <= now),
        db.or_(Deal.end_date.is_(None), Deal.end_date >= now),
    ).order_by(Deal.display_order.asc(), Deal.id.desc()).all()
    return jsonify({'deals': [deal.to_dict() for deal in deals]})


@deals_bp.route('/admin/deals', methods=['GET', 'POST'])
def manage_deals():
    if get_authenticated_admin() is None:
        return jsonify({'error': 'Unauthorized'}), 401

    if request.method == 'POST':
        payload = request.get_json(silent=True) or {}
        title = str(payload.get('title') or '').strip()
        if not title:
            return jsonify({'error': 'Deal title is required.'}), 400
        product_ids = payload.get('product_ids') or []
        if not isinstance(product_ids, list):
            return jsonify({'error': 'product_ids must be a list.'}), 400
        deal = Deal(
            title=title,
            description=str(payload.get('description') or ''),
            image_url=str(payload.get('image_url') or ''),
            deal_type=str(payload.get('deal_type') or 'bundle'),
            original_price=float(payload.get('original_price') or 0),
            deal_price=float(payload.get('deal_price') or 0),
            discount_info=str(payload.get('discount_info') or ''),
            product_ids=json.dumps([int(product_id) for product_id in product_ids]),
            start_date=parse_datetime(payload.get('start_date')),
            end_date=parse_datetime(payload.get('end_date')),
            is_active=bool(payload.get('is_active', True)),
            is_featured=bool(payload.get('is_featured', False)),
            display_order=int(payload.get('display_order') or 0),
        )
        db.session.add(deal)
        db.session.commit()
        return jsonify({'deal': deal.to_dict()}), 201

    deals = Deal.query.order_by(Deal.display_order.asc(), Deal.id.desc()).all()
    return jsonify({'deals': [deal.to_dict() for deal in deals]})


@deals_bp.route('/admin/deals/<int:deal_id>', methods=['PUT', 'DELETE'])
def manage_deal(deal_id):
    if get_authenticated_admin() is None:
        return jsonify({'error': 'Unauthorized'}), 401

    deal = Deal.query.get_or_404(deal_id)
    if request.method == 'DELETE':
        db.session.delete(deal)
        db.session.commit()
        return jsonify({'deleted': True, 'id': deal_id})

    payload = request.get_json(silent=True) or {}
    for field in ('title', 'description', 'image_url', 'deal_type', 'discount_info'):
        if field in payload:
            setattr(deal, field, str(payload[field]).strip() if field == 'title' else str(payload[field]))
    if 'original_price' in payload:
        deal.original_price = float(payload.get('original_price') or 0)
    if 'deal_price' in payload:
        deal.deal_price = float(payload.get('deal_price') or 0)
    if 'product_ids' in payload:
        product_ids = payload.get('product_ids') or []
        if not isinstance(product_ids, list):
            return jsonify({'error': 'product_ids must be a list.'}), 400
        deal.product_ids = json.dumps([int(product_id) for product_id in product_ids])
    if 'start_date' in payload:
        deal.start_date = parse_datetime(payload.get('start_date'))
    if 'end_date' in payload:
        deal.end_date = parse_datetime(payload.get('end_date'))
    if 'is_active' in payload:
        deal.is_active = bool(payload['is_active'])
    if 'is_featured' in payload:
        deal.is_featured = bool(payload['is_featured'])
    if 'display_order' in payload:
        deal.display_order = int(payload['display_order'] or 0)
    db.session.commit()
    return jsonify({'deal': deal.to_dict()})
