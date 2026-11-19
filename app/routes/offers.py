from datetime import datetime

from flask import Blueprint, jsonify, request

from app.extensions import db
from app.models import Offer, Product
from app.routes.auth import get_authenticated_admin

offers_bp = Blueprint('offers', __name__, url_prefix='/api')


@offers_bp.get('/offers')
def list_offers():
    now = datetime.utcnow()
    offers = Offer.query.filter(Offer.is_published.is_(True)).all()
    active = []
    for offer in offers:
        if offer.start_date and offer.start_date > now:
            continue
        if offer.expiry_date and offer.expiry_date < now:
            continue
        offer_data = offer.to_dict()
        if offer.product_id is not None:
            product = Product.query.get(offer.product_id)
            if product:
                offer_data['product_id'] = product.id
                offer_data['product_name'] = product.name
                offer_data['product_image_url'] = product.image_url
        active.append(offer_data)
    return jsonify({'offers': active})


@offers_bp.route('/admin/offers', methods=['GET', 'POST'])
def admin_offers():
    if get_authenticated_admin() is None:
        return jsonify({'error': 'Unauthorized'}), 401

    if request.method == 'POST':
        payload = request.get_json(silent=True) or {}
        product_id = payload.get('product_id')
        if product_id and Product.query.get(product_id) is None:
            return jsonify({'error': 'Product not found.'}), 404

        offer = Offer(
            product_id=product_id,
            title=payload.get('title', 'New Offer'),
            description=payload.get('description', ''),
            image_url=payload.get('image_url'),
            badge=payload.get('badge', 'OFFER'),
            discount_type=payload.get('discount_type', 'percentage'),
            discount_value=float(payload.get('discount_value', 0) or 0),
            original_price=float(payload.get('original_price', 0) or 0),
            promo_price=float(payload.get('promo_price', 0) or 0),
            start_date=datetime.fromisoformat(payload['start_date']) if payload.get('start_date') else None,
            expiry_date=datetime.fromisoformat(payload['expiry_date']) if payload.get('expiry_date') else None,
            cta_label=payload.get('cta_label', 'Shop Offers'),
            cta_url=payload.get('cta_url', '#offers'),
            is_published=bool(payload.get('is_published', True)),
        )
        db.session.add(offer)
        db.session.commit()
        return jsonify({'offer': offer.to_dict()}), 201

    offers = [offer.to_dict() for offer in Offer.query.order_by(Offer.id.desc()).all()]
    return jsonify({'offers': offers})


@offers_bp.route('/admin/offers/<int:offer_id>', methods=['PUT', 'DELETE'])
def manage_offer(offer_id):
    if get_authenticated_admin() is None:
        return jsonify({'error': 'Unauthorized'}), 401

    offer = Offer.query.get_or_404(offer_id)
    if request.method == 'PUT':
        payload = request.get_json(silent=True) or {}
        if payload.get('product_id') and Product.query.get(payload['product_id']) is None:
            return jsonify({'error': 'Product not found.'}), 404
        offer.product_id = payload.get('product_id', offer.product_id)
        offer.title = payload.get('title', offer.title)
        offer.description = payload.get('description', offer.description)
        offer.image_url = payload.get('image_url', offer.image_url)
        offer.badge = payload.get('badge', offer.badge)
        offer.discount_type = payload.get('discount_type', offer.discount_type)
        offer.discount_value = float(payload.get('discount_value', offer.discount_value) or 0)
        offer.original_price = float(payload.get('original_price', offer.original_price) or 0)
        offer.promo_price = float(payload.get('promo_price', offer.promo_price) or 0)
        offer.cta_label = payload.get('cta_label', offer.cta_label)
        offer.cta_url = payload.get('cta_url', offer.cta_url)
        if payload.get('start_date'):
            offer.start_date = datetime.fromisoformat(payload['start_date'])
        if payload.get('expiry_date'):
            offer.expiry_date = datetime.fromisoformat(payload['expiry_date'])
        offer.is_published = payload.get('is_published', offer.is_published)
        db.session.commit()
        return jsonify({'offer': offer.to_dict()})

    db.session.delete(offer)
    db.session.commit()
    return jsonify({'deleted': True, 'id': offer_id})
