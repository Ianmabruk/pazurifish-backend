import os

from flask import Flask, jsonify
from flask_cors import CORS
from sqlalchemy import inspect, text
from werkzeug.security import generate_password_hash

from app.config import Config
from app.extensions import db
from app.models import AdminUser, Category, HeroContent, Offer, Order, OrderItem, Product, Sale, SaleItem, StockMovement, WhatsAppMessage
from app.routes.admin import admin_bp
from app.routes.auth import auth_bp
from app.routes.content import content_bp
from app.routes.offers import offers_bp
from app.routes.orders import orders_bp
from app.routes.products import products_bp
from app.routes.whatsapp import whatsapp_bp
from app.routes.categories import categories_bp


def ensure_schema_compatibility():
    inspector = inspect(db.engine)
    tables = set(inspector.get_table_names())

    if 'products' in tables:
        product_columns = {column['name'] for column in inspector.get_columns('products')}
        if 'specifications' not in product_columns:
            with db.engine.begin() as conn:
                conn.execute(text('ALTER TABLE products ADD COLUMN specifications TEXT DEFAULT ""'))
        if 'is_available' not in product_columns:
            with db.engine.begin() as conn:
                conn.execute(text('ALTER TABLE products ADD COLUMN is_available BOOLEAN DEFAULT 1'))

    if 'offers' in tables:
        offer_columns = {column['name'] for column in inspector.get_columns('offers')}
        if 'product_id' not in offer_columns:
            with db.engine.begin() as conn:
                conn.execute(text('ALTER TABLE offers ADD COLUMN product_id INTEGER'))
        if 'cta_label' not in offer_columns:
            with db.engine.begin() as conn:
                conn.execute(text("ALTER TABLE offers ADD COLUMN cta_label VARCHAR(80) DEFAULT 'Shop Offers'"))
        if 'cta_url' not in offer_columns:
            with db.engine.begin() as conn:
                conn.execute(text("ALTER TABLE offers ADD COLUMN cta_url VARCHAR(500) DEFAULT '#offers'"))

    if 'admin_users' in tables:
        admin_columns = {column['name'] for column in inspector.get_columns('admin_users')}
        if 'password_hash' not in admin_columns:
            with db.engine.begin() as conn:
                conn.execute(text('ALTER TABLE admin_users ADD COLUMN password_hash VARCHAR(255)'))

    if 'hero_content' in tables:
        hero_columns = {column['name'] for column in inspector.get_columns('hero_content')}
        if 'sort_order' not in hero_columns:
            with db.engine.begin() as conn:
                conn.execute(text('ALTER TABLE hero_content ADD COLUMN sort_order INTEGER DEFAULT 0'))
        for column_name, ddl in {
            'description': 'ALTER TABLE hero_content ADD COLUMN description VARCHAR(500) DEFAULT ""',
            'cta_label': "ALTER TABLE hero_content ADD COLUMN cta_label VARCHAR(80) DEFAULT ''",
            'cta_url': "ALTER TABLE hero_content ADD COLUMN cta_url VARCHAR(500) DEFAULT ''",
        }.items():
            if column_name not in hero_columns:
                with db.engine.begin() as conn:
                    conn.execute(text(ddl))

    if 'sales' in tables:
        sale_columns = {column['name'] for column in inspector.get_columns('sales')}
        if 'source' not in sale_columns:
            with db.engine.begin() as conn:
                conn.execute(text('ALTER TABLE sales ADD COLUMN source VARCHAR(40) DEFAULT "POS"'))


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    cors_origins = [
        origin.strip()
        for origin in os.getenv('CORS_ORIGINS', 'http://localhost:5173,http://localhost:4173,http://localhost:4174').split(',')
        if origin.strip()
    ]
    CORS(
        app,
        resources={r'/api/*': {'origins': cors_origins}},
        methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
        allow_headers=['Content-Type', 'Authorization'],
    )

    with app.app_context():
        db.create_all()
        ensure_schema_compatibility()

        if Product.query.count() == 0:
            default_products = [
                Product(
                    sku='PF-001',
                    name='Fresh Whole Tilapia',
                    description='Fresh whole tilapia, selected for your table.',
                    specifications='Lake Victoria fresh catch; ideal for grilling, frying and stews; locally sourced.',
                    category='Fish Butchery',
                    selling_price=650,
                    cost_price=480,
                    unit='per kg',
                    image_url='https://images.unsplash.com/photo-1544943910-4c1dc44aab77?auto=format&fit=crop&w=900&q=80',
                    stock_quantity=25,
                    minimum_stock=5,
                    is_available=True,
                ),
                Product(
                    sku='PF-002',
                    name='Fresh Juice',
                    description='Refreshing fruit juice to pair with your fish meal.',
                    specifications='Prepared daily with fresh ingredients for a crisp, clean finish.',
                    category='Drinks',
                    selling_price=250,
                    cost_price=150,
                    unit='per bottle',
                    image_url='https://images.unsplash.com/photo-1546173159-315724a31696?auto=format&fit=crop&w=900&q=80',
                    stock_quantity=30,
                    minimum_stock=8,
                    is_available=True,
                ),
                Product(
                    sku='PF-003',
                    name='Tilapia Fillet',
                    description='Convenient fillets for everyday cooking.',
                    specifications='Cleaned, portioned and ready for quick prep at home or in the kitchen.',
                    category='Fish Butchery',
                    selling_price=1100,
                    cost_price=810,
                    unit='per kg',
                    image_url='https://images.unsplash.com/photo-1519708227418-c8fd9a32b7a2?auto=format&fit=crop&w=900&q=80',
                    stock_quantity=12,
                    minimum_stock=3,
                    is_available=True,
                ),
                Product(
                    sku='PF-004',
                    name='Fish Fingers',
                    description='Easy-to-prepare fish portions.',
                    specifications='Lightly seasoned and ideal for quick family meals.',
                    category='Fish Butchery',
                    selling_price=750,
                    cost_price=520,
                    unit='per pack',
                    image_url='https://images.unsplash.com/photo-1510130387422-82bed34b37e9?auto=format&fit=crop&w=900&q=80',
                    stock_quantity=18,
                    minimum_stock=4,
                    is_available=True,
                ),
                Product(
                    sku='PF-005',
                    name='Grilled Tilapia',
                    description='A freshly prepared kitchen favourite.',
                    specifications='Perfectly grilled and served ready for immediate dining.',
                    category='Kitchen',
                    selling_price=1200,
                    cost_price=870,
                    unit='per serving',
                    image_url='https://images.unsplash.com/photo-1559847844-5315695dadae?auto=format&fit=crop&w=900&q=80',
                    stock_quantity=16,
                    minimum_stock=3,
                    is_available=True,
                ),
                Product(
                    sku='PF-006',
                    name='Fish and Chips',
                    description='A satisfying classic meal.',
                    specifications='Crisp golden chips paired with fresh fish for a favourite comfort meal.',
                    category='Kitchen',
                    selling_price=950,
                    cost_price=680,
                    unit='per serving',
                    image_url='https://images.unsplash.com/photo-1579208030886-b937da0925dc?auto=format&fit=crop&w=900&q=80',
                    stock_quantity=14,
                    minimum_stock=3,
                    is_available=True,
                ),
                Product(
                    sku='PF-007',
                    name='Family Fish Combo',
                    description='A generous selection for sharing.',
                    specifications='Curated to serve families and gatherings with variety and value.',
                    category='Combos',
                    selling_price=2400,
                    cost_price=1700,
                    unit='per combo',
                    image_url='https://images.unsplash.com/photo-1515516969-d4008cc6241a?auto=format&fit=crop&w=900&q=80',
                    stock_quantity=10,
                    minimum_stock=2,
                    is_available=True,
                ),
                Product(
                    sku='PF-008',
                    name='Fresh Nile Perch',
                    description='Quality Nile perch, prepared to order.',
                    specifications='Premium fillets and cuts for family meals and restaurant use.',
                    category='Fish Butchery',
                    selling_price=850,
                    cost_price=620,
                    unit='per kg',
                    image_url='https://images.unsplash.com/photo-1535399831218-d5bd36d1a6b3?auto=format&fit=crop&w=900&q=80',
                    stock_quantity=18,
                    minimum_stock=4,
                    is_available=True,
                ),
            ]
            db.session.add_all(default_products)

        if AdminUser.query.filter_by(email='admin@pazurifish.local').first() is None:
            db.session.add(AdminUser(
                email='admin@pazurifish.local',
                full_name='Pazuri Fish Administrator',
                role='administrator',
                password_hash=generate_password_hash('ChangeMe123!'),
            ))

        if HeroContent.query.count() == 0:
            db.session.add_all([
                HeroContent(
                    title='FRESH CATCH, DELIVERED EVERY DAY.',
                    subtitle='FRESH FROM LAKE VICTORIA',
                    image_url='https://images.unsplash.com/photo-1544943910-4c1dc44aab77?auto=format&fit=crop&w=1200&q=80',
                    sort_order=0,
                    is_published=True,
                ),
                HeroContent(
                    title='FROM THE LAKE TO YOUR KITCHEN.',
                    subtitle='HAND-PICKED DAILY',
                    image_url='https://images.unsplash.com/photo-1559847844-5315695dadae?auto=format&fit=crop&w=1200&q=80',
                    sort_order=1,
                    is_published=True,
                ),
                HeroContent(
                    title='FAMILY MEALS, FRESHLY PREPARED.',
                    subtitle='PREMIUM SEAFOOD, SIMPLY SERVED',
                    image_url='https://images.unsplash.com/photo-1535399831218-d5bd36d1a6b3?auto=format&fit=crop&w=1200&q=80',
                    sort_order=2,
                    is_published=True,
                ),
            ])

        if Offer.query.count() == 0:
            first_product = Product.query.first()
            db.session.add_all([
                Offer(
                    title='Fresh Tilapia Special',
                    description='Special prices on selected fresh tilapia.',
                    product_id=first_product.id if first_product else None,
                    image_url='https://images.unsplash.com/photo-1544943910-4c1dc44aab77?auto=format&fit=crop&w=900&q=80',
                    badge='OFFER 01',
                    discount_type='percentage',
                    discount_value=10,
                    original_price=850,
                    promo_price=760,
                    is_published=True,
                ),
                Offer(
                    title='Family Fish Combo',
                    description='Enjoy our family fish selection.',
                    product_id=first_product.id if first_product else None,
                    image_url='https://images.unsplash.com/photo-1515516969-d4008cc6241a?auto=format&fit=crop&w=900&q=80',
                    badge='OFFER 02',
                    discount_type='percentage',
                    discount_value=12,
                    original_price=2400,
                    promo_price=2100,
                    is_published=True,
                ),
                Offer(
                    title='Weekend Specials',
                    description='Discover our latest weekend offers.',
                    product_id=first_product.id if first_product else None,
                    image_url='https://images.unsplash.com/photo-1510130387422-82bed34b37e9?auto=format&fit=crop&w=900&q=80',
                    badge='OFFER 03',
                    discount_type='percentage',
                    discount_value=15,
                    original_price=1200,
                    promo_price=1020,
                    is_published=True,
                ),
            ])

        if Category.query.count() == 0:
            default_categories = [
                Category(name='Fish Butchery', image_url='https://images.unsplash.com/photo-1544943910-4c1dc44aab77?auto=format&fit=crop&w=900&q=80', display_order=0, is_active=True, show_on_homepage=True),
                Category(name='Kitchen', image_url='https://images.unsplash.com/photo-1559847844-5315695dadae?auto=format&fit=crop&w=900&q=80', display_order=1, is_active=True, show_on_homepage=True),
                Category(name='Combos', image_url='https://images.unsplash.com/photo-1515516969-d4008cc6241a?auto=format&fit=crop&w=900&q=80', display_order=2, is_active=True, show_on_homepage=True),
                Category(name='Drinks', image_url='https://images.unsplash.com/photo-1546173159-315724a31696?auto=format&fit=crop&w=900&q=80', display_order=3, is_active=True, show_on_homepage=True),
            ]
            db.session.add_all(default_categories)

        db.session.commit()

    app.register_blueprint(products_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(content_bp)
    app.register_blueprint(offers_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(whatsapp_bp)
    app.register_blueprint(categories_bp)

    @app.route('/api/health')
    def health():
        return jsonify({'status': 'ok'})

    return app


app = create_app()
