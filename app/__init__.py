import os
import json
from datetime import datetime, timedelta

from flask import Flask, jsonify
from flask_cors import CORS
from sqlalchemy import inspect, text
from werkzeug.security import generate_password_hash

from app.config import Config
from app.extensions import db
from app.models import AdminUser, Category, HeroContent, Offer, Order, OrderItem, OrderStatusUpdate, Product, Sale, SaleItem, StockMovement, WhatsAppMessage
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
        for column_name, ddl in {
            'featured': 'ALTER TABLE products ADD COLUMN featured BOOLEAN DEFAULT 0',
            'status': "ALTER TABLE products ADD COLUMN status VARCHAR(20) DEFAULT 'Active'",
            'discount_price': 'ALTER TABLE products ADD COLUMN discount_price FLOAT',
            'serving_sizes': 'ALTER TABLE products ADD COLUMN serving_sizes TEXT DEFAULT ""',
        }.items():
            if column_name not in product_columns:
                with db.engine.begin() as conn:
                    conn.execute(text(ddl))

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

    if 'orders' in tables:
        order_columns = {column['name'] for column in inspector.get_columns('orders')}
        if 'tracking_number' not in order_columns:
            with db.engine.begin() as conn:
                conn.execute(text('ALTER TABLE orders ADD COLUMN tracking_number VARCHAR(80)'))
        if 'idempotency_key' not in order_columns:
            with db.engine.begin() as conn:
                conn.execute(text('ALTER TABLE orders ADD COLUMN idempotency_key VARCHAR(100)'))
        for order in Order.query.filter(Order.tracking_number.is_(None)).all():
            order.tracking_number = f"PAZ-{order.created_at.strftime('%Y%m%d') if order.created_at else datetime.utcnow().strftime('%Y%m%d')}-{order.id:06d}"
        db.session.commit()


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

        for kitchen_product in Product.query.filter(db.func.lower(Product.category) == 'kitchen').all():
            if not kitchen_product.serving_sizes:
                kitchen_product.serving_sizes = json.dumps(['1 Person', '2–3 People', '4–5 People', '6–7 People'])
        db.session.commit()

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
                    serving_sizes=json.dumps(['1 Person', '2–3 People', '4–5 People', '6–7 People']),
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
                    serving_sizes=json.dumps(['1 Person', '2–3 People', '4–5 People', '6–7 People']),
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

        category_products = [
            ('PF-FISH-01', 'Fresh Whole Tilapia', 'Fish Butchery', 'Whole Lake Victoria tilapia, cleaned and prepared to order.', 760, 'per kg', '/images/categories/fish-butchery/tilapia.jpg'),
            ('PF-FISH-02', 'Fresh Nile Perch Fillet', 'Fish Butchery', 'Boneless Nile perch fillet, portioned for easy cooking.', 1250, 'per kg', '/images/categories/fish-butchery/nile-perch.jpg'),
            ('PF-FISH-03', 'Fresh Fish Cuts', 'Fish Butchery', 'A selection of fresh fish cuts, ready for your preferred recipe.', 850, 'per kg', '/images/categories/fish-butchery/fish-cuts.jpg'),
            ('PF-COMBO-01', 'Family Seafood Feast', 'Combos', 'A shareable seafood selection with fresh fish and sides.', 3200, 'per combo', '/images/categories/combos/family-feast.jpg'),
            ('PF-COMBO-02', 'Tilapia and Perch Duo', 'Combos', 'A fresh pairing of tilapia and Nile perch for the table.', 2800, 'per combo', '/images/categories/combos/grill-box.jpg'),
            ('PF-COMBO-03', 'Grill Night Seafood Box', 'Combos', 'A mix of grill-ready seafood portions for a family meal.', 3500, 'per box', '/images/categories/combos/supper-bundle.jpg'),
            ('PF-COMBO-04', 'Fish Supper Bundle', 'Combos', 'Fresh fish portions paired with a classic side.', 1950, 'per combo', '/images/products/fish-and-chips.jpg'),
            ('PF-COMBO-05', 'Lake Catch Sharing Pack', 'Combos', 'A selection of Lake Victoria fish cuts to share.', 2600, 'per pack', '/images/products/family-combo.jpg'),
            ('PF-COMBO-06', 'Weekend Seafood Mix', 'Combos', 'A varied seafood selection prepared for weekend cooking.', 3000, 'per combo', '/images/products/fresh-fish.jpg'),
            ('PF-KITCHEN-01', 'Grilled Tilapia Meal', 'Kitchen', 'A freshly grilled tilapia meal, served with a choice of sides.', 1450, 'per serving', '/images/categories/kitchen/grilled-tilapia.jpg'),
            ('PF-KITCHEN-02', 'Fish and Chips', 'Kitchen', 'Crisp golden chips served with freshly prepared fish.', 1050, 'per serving', '/images/categories/kitchen/fish-and-chips.jpg'),
            ('PF-KITCHEN-03', 'Pan-Seared Nile Perch', 'Kitchen', 'Tender Nile perch, pan-seared and served ready to enjoy.', 1650, 'per serving', '/images/categories/kitchen/pan-seared-perch.jpg'),
            ('PF-KITCHEN-04', 'Crispy Fish Fillet Plate', 'Kitchen', 'A golden fish fillet plate prepared fresh to order.', 1250, 'per serving', '/images/products/fish-cuts.jpg'),
            ('PF-KITCHEN-05', 'Seafood Rice Bowl', 'Kitchen', 'A hearty seafood bowl with seasoned rice and fresh vegetables.', 1350, 'per serving', '/images/products/kitchen-meal.jpg'),
            ('PF-KITCHEN-06', 'Family Fish Platter', 'Kitchen', 'A prepared fish platter designed for sharing.', 2400, 'per platter', '/images/products/family-combo.jpg'),
            ('PF-DRINK-01', 'Tropical Fruit Cooler', 'Drinks', 'A chilled fruit cooler with a bright, tropical finish.', 280, 'per bottle', '/images/categories/drinks/tropical-cooler.jpg'),
            ('PF-DRINK-02', 'Orange Sunrise Juice', 'Drinks', 'A bright orange juice served chilled.', 300, 'per bottle', '/images/categories/drinks/orange-juice.jpg'),
            ('PF-DRINK-03', 'Iced Hibiscus Cooler', 'Drinks', 'A refreshing hibiscus cooler with a hint of citrus.', 280, 'per glass', '/images/categories/drinks/hibiscus-cooler.jpg'),
            ('PF-DRINK-04', 'Tropical Smoothie', 'Drinks', 'A smooth tropical fruit blend, served cold.', 350, 'per bottle', '/images/categories/drinks/tropical-smoothie.jpg'),
            ('PF-DRINK-05', 'Lemon Mint Cooler', 'Drinks', 'A cool lemon and mint drink for a refreshing pairing.', 280, 'per glass', '/images/categories/drinks/lemon-mint.jpg'),
            ('PF-DRINK-06', 'Passion Fruit Juice', 'Drinks', 'A chilled passion fruit juice with a tangy finish.', 300, 'per bottle', '/images/categories/drinks/passion-fruit.jpg'),
        ]
        seeded_products_by_sku = {sku: details for sku, *details in category_products}
        legacy_skus = [sku.replace('PF-', 'DEMO-', 1) for sku, *_ in category_products]
        legacy_products = Product.query.filter(Product.sku.in_(legacy_skus)).all()
        existing_skus = {sku for (sku,) in Product.query.with_entities(Product.sku).all()}
        for product in legacy_products:
            category_sku = product.sku.replace('DEMO-', 'PF-', 1)
            if category_sku in existing_skus:
                product.is_available = False
                product.stock_quantity = 0
                continue
            product.sku = category_sku
            product.description = seeded_products_by_sku[category_sku][2]
            product.specifications = 'Prepared and packed for customer orders.'
            if product.category == 'Kitchen' and not product.serving_sizes:
                product.serving_sizes = json.dumps(['1 Person', '2–3 People', '4–5 People', '6–7 People'])
            existing_skus.add(category_sku)

        db.session.flush()
        for category in ('Fish Butchery', 'Combos', 'Kitchen', 'Drinks'):
            category_stock = Product.query.filter(
                db.func.lower(Product.category) == category.lower(),
                Product.is_available.is_(True),
                Product.stock_quantity > 0,
            ).count()
            for sku, name, product_category, description, price, unit, image_url in category_products:
                if product_category != category or category_stock >= 3 or sku in existing_skus:
                    continue
                db.session.add(Product(
                    sku=sku,
                    name=name,
                    description=description,
                    specifications='Prepared and packed for customer orders.',
                    category=product_category,
                    selling_price=price,
                    unit=unit,
                    image_url=image_url,
                    stock_quantity=20,
                    minimum_stock=2,
                    is_available=True,
                    serving_sizes=json.dumps(['1 Person', '2–3 People', '4–5 People', '6–7 People']) if product_category == 'Kitchen' else '',
                ))
                existing_skus.add(sku)
                category_stock += 1


        demo_hero_slides = [
            ('Demo hero: Fresh seafood', '/images/hero-seafood.png'),
            ('Demo hero: Fresh fish', '/images/products/fresh-fish.jpg'),
            ('Demo hero: Nile perch', '/images/products/nile-perch.jpg'),
            ('Demo hero: Fish cuts', '/images/products/fish-cuts.jpg'),
            ('Demo hero: Family combo', '/images/products/family-combo.jpg'),
            ('Demo hero: Fish and chips', '/images/products/fish-and-chips.jpg'),
        ]
        existing_hero_slides = HeroContent.query.all()
        existing_hero_titles = {slide.title for slide in existing_hero_slides}
        next_hero_order = max((slide.sort_order or 0 for slide in existing_hero_slides), default=-1) + 1
        for image_index, (title, image_url) in enumerate(demo_hero_slides):
            if title in existing_hero_titles:
                continue
            db.session.add(HeroContent(
                title=title,
                subtitle='FRESH FROM LAKE VICTORIA',
                image_url=image_url,
                sort_order=next_hero_order + image_index,
                is_published=True,
            ))

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

        active_deals = [
            ('Fresh Tilapia Special', 'A fresh lake tilapia special for everyday family meals.', 'Fish Butchery', 850, 760, '/images/products/fresh-fish.jpg'),
            ('Family Seafood Combo', 'A generous seafood combo prepared for sharing.', 'Combos', 2400, 2100, '/images/categories/combos/family-feast.jpg'),
            ('Seafood Kitchen Meal Deal', 'A satisfying prepared seafood meal with a choice of sides.', 'Kitchen', 1450, 1250, '/images/categories/kitchen/grilled-tilapia.jpg'),
        ]
        deal_now = datetime.utcnow()
        deal_expiry = deal_now + timedelta(days=30)
        for deal_index, (title, description, category_name, original_price, promo_price, image_url) in enumerate(active_deals):
            if Offer.query.filter_by(title=title).first():
                continue
            product = Product.query.filter(db.func.lower(Product.category) == category_name.lower()).first()
            db.session.add(Offer(
                product_id=product.id if product else None,
                title=title,
                description=description,
                image_url=image_url,
                badge=f'DEAL {deal_index + 1}',
                discount_type='percentage',
                discount_value=round((1 - promo_price / original_price) * 100),
                original_price=original_price,
                promo_price=promo_price,
                start_date=deal_now,
                expiry_date=deal_expiry,
                cta_label='View Deal',
                cta_url='#deals',
                is_published=True,
            ))

        if Category.query.count() == 0:
            default_categories = [
                Category(name='Fish Butchery', image_url='https://images.unsplash.com/photo-1544943910-4c1dc44aab77?auto=format&fit=crop&w=900&q=80', display_order=0, is_active=True, show_on_homepage=True),
                Category(name='Kitchen', image_url='https://images.unsplash.com/photo-1559847844-5315695dadae?auto=format&fit=crop&w=900&q=80', display_order=1, is_active=True, show_on_homepage=True),
                Category(name='Combos', image_url='https://images.unsplash.com/photo-1515516969-d4008cc6241a?auto=format&fit=crop&w=900&q=80', display_order=2, is_active=True, show_on_homepage=True),
                Category(name='Drinks', image_url='https://images.unsplash.com/photo-1546173159-315724a31696?auto=format&fit=crop&w=900&q=80', display_order=3, is_active=True, show_on_homepage=True),
                Category(name='Other', image_url='/images/products/fresh-fish.jpg', display_order=4, is_active=True, show_on_homepage=True),
            ]
            db.session.add_all(default_categories)

        if Category.query.filter(db.func.lower(Category.name) == 'other').first() is None:
            db.session.add(Category(
                name='Other',
                image_url='/images/products/fresh-fish.jpg',
                display_order=4,
                is_active=True,
                show_on_homepage=True,
            ))

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
