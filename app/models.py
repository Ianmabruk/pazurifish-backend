from datetime import datetime

from app.extensions import db


class Product(db.Model):
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(100), unique=True, nullable=False, default='PF-0001')
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    specifications = db.Column(db.Text, default='')
    category = db.Column(db.String(80), default='Fish Butchery')
    selling_price = db.Column(db.Float, nullable=False, default=0.0)
    cost_price = db.Column(db.Float, default=0.0)
    unit = db.Column(db.String(50), default='per kg')
    image_url = db.Column(db.String(500))
    stock_quantity = db.Column(db.Integer, default=0)
    minimum_stock = db.Column(db.Integer, default=0)
    is_available = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'sku': self.sku,
            'name': self.name,
            'description': self.description,
            'specifications': self.specifications or '',
            'category': self.category,
            'price': float(self.selling_price),
            'selling_price': float(self.selling_price),
            'cost_price': float(self.cost_price or 0),
            'unit': self.unit,
            'image_url': self.image_url,
            'stock_quantity': self.stock_quantity,
            'minimum_stock': self.minimum_stock,
            'is_available': self.is_available,
            'image': self.image_url,
        }


class Offer(db.Model):
    __tablename__ = 'offers'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'))
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(500))
    badge = db.Column(db.String(80), default='OFFER')
    discount_type = db.Column(db.String(40), default='percentage')
    discount_value = db.Column(db.Float, default=0.0)
    original_price = db.Column(db.Float, default=0.0)
    promo_price = db.Column(db.Float, default=0.0)
    start_date = db.Column(db.DateTime)
    expiry_date = db.Column(db.DateTime)
    cta_label = db.Column(db.String(80), default='Shop Offers')
    cta_url = db.Column(db.String(500), default='#offers')
    is_published = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    product = db.relationship('Product', backref='offers', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'product_name': self.product.name if self.product else None,
            'title': self.title,
            'description': self.description,
            'image_url': self.image_url,
            'badge': self.badge,
            'discount_type': self.discount_type,
            'discount_value': self.discount_value,
            'original_price': self.original_price,
            'promo_price': self.promo_price,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None,
            'ends_at': self.expiry_date.isoformat() if self.expiry_date else None,
            'cta_label': self.cta_label or 'Shop Offers',
            'cta_url': self.cta_url or '#offers',
            'is_published': self.is_published,
        }


class HeroContent(db.Model):
    __tablename__ = 'hero_content'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), default='FRESH CATCH, DELIVERED EVERY DAY.')
    subtitle = db.Column(db.String(200), default='FRESH FROM LAKE VICTORIA')
    description = db.Column(db.String(500), default='')
    cta_label = db.Column(db.String(80), default='')
    cta_url = db.Column(db.String(500), default='')
    image_url = db.Column(db.String(500), default='https://images.unsplash.com/photo-1544943910-4c1dc44aab77?auto=format&fit=crop&w=1200&q=80')
    sort_order = db.Column(db.Integer, default=0)
    is_published = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'subtitle': self.subtitle,
            'description': self.description or '',
            'cta_label': self.cta_label or '',
            'cta_url': self.cta_url or '',
            'image_url': self.image_url,
            'sort_order': self.sort_order,
            'is_published': self.is_published,
        }


class AdminUser(db.Model):
    __tablename__ = 'admin_users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(200), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(200), default='Administrator')
    role = db.Column(db.String(80), default='administrator')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'full_name': self.full_name,
            'role': self.role,
        }


class Customer(db.Model):
    __tablename__ = 'customers'

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Order(db.Model):
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(80), unique=True, nullable=False)
    customer_name = db.Column(db.String(200))
    customer_phone = db.Column(db.String(80))
    delivery_area = db.Column(db.String(100), default='Nairobi')
    delivery_address = db.Column(db.String(200))
    source = db.Column(db.String(40), default='ONLINE')
    subtotal = db.Column(db.Float, default=0.0)
    discount = db.Column(db.Float, default=0.0)
    delivery_fee = db.Column(db.Float, default=0.0)
    total = db.Column(db.Float, default=0.0)
    order_status = db.Column(db.String(80), default='PENDING_CONFIRMATION')
    payment_status = db.Column(db.String(80), default='PENDING')
    whatsapp_status = db.Column(db.String(80), default='PENDING')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'order_number': self.order_number,
            'customer_name': self.customer_name,
            'customer_phone': self.customer_phone,
            'delivery_area': self.delivery_area,
            'delivery_address': self.delivery_address,
            'source': self.source,
            'subtotal': float(self.subtotal),
            'discount': float(self.discount),
            'delivery_fee': float(self.delivery_fee),
            'total': float(self.total),
            'status': self.order_status,
            'order_status': self.order_status,
            'payment_status': self.payment_status,
            'whatsapp_status': self.whatsapp_status,
            'items': [item.to_dict() for item in self.items],
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class OrderItem(db.Model):
    __tablename__ = 'order_items'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'))
    product_name = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'product_name': self.product_name,
            'quantity': self.quantity,
            'unit_price': float(self.unit_price),
            'total_price': float(self.total_price),
        }


class Sale(db.Model):
    __tablename__ = 'sales'

    id = db.Column(db.Integer, primary_key=True)
    receipt_number = db.Column(db.String(80), unique=True, nullable=False)
    cashier_id = db.Column(db.String(80), default='cashier')
    source = db.Column(db.String(40), default='POS')
    subtotal = db.Column(db.Float, default=0.0)
    discount = db.Column(db.Float, default=0.0)
    total = db.Column(db.Float, default=0.0)
    payment_method = db.Column(db.String(80), default='Cash')
    payment_reference = db.Column(db.String(120))
    sale_status = db.Column(db.String(80), default='COMPLETED')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    items = db.relationship('SaleItem', backref='sale', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'receipt_number': self.receipt_number,
            'cashier_id': self.cashier_id,
            'subtotal': float(self.subtotal),
            'discount': float(self.discount),
            'total': float(self.total),
            'payment_method': self.payment_method,
            'payment_reference': self.payment_reference,
            'sale_status': self.sale_status,
            'items': [item.to_dict() for item in self.items],
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class SaleItem(db.Model):
    __tablename__ = 'sale_items'

    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sales.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'))
    product_name = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'product_name': self.product_name,
            'quantity': self.quantity,
            'unit_price': float(self.unit_price),
            'total_price': float(self.total_price),
        }


class StockMovement(db.Model):
    __tablename__ = 'stock_movements'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    movement_type = db.Column(db.String(80), nullable=False)
    quantity_before = db.Column(db.Integer, default=0)
    quantity_changed = db.Column(db.Integer, default=0)
    quantity_after = db.Column(db.Integer, default=0)
    reason = db.Column(db.String(200), default='manual-adjustment')
    reference_type = db.Column(db.String(80), default='manual')
    reference_id = db.Column(db.String(120))
    user_id = db.Column(db.String(120), default='system')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class WhatsAppMessage(db.Model):
    __tablename__ = 'whatsapp_messages'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'))
    message_id = db.Column(db.String(200), nullable=False)
    recipient = db.Column(db.String(120))
    message_type = db.Column(db.String(80), default='outbound')
    delivery_status = db.Column(db.String(80), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'order_id': self.order_id,
            'message_id': self.message_id,
            'recipient': self.recipient,
            'message_type': self.message_type,
            'delivery_status': self.delivery_status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    image_url = db.Column(db.String(500), default='')
    display_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    show_on_homepage = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'image_url': self.image_url or '',
            'display_order': self.display_order,
            'is_active': self.is_active,
            'show_on_homepage': self.show_on_homepage,
        }
