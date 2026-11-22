import os

from app import create_app


def test_health_check():
    app = create_app()
    client = app.test_client()

    response = client.get('/api/health')
    assert response.status_code == 200
    assert response.get_json()['status'] == 'ok'


def test_product_list_endpoint():
    app = create_app()
    client = app.test_client()

    response = client.get('/api/products')
    assert response.status_code == 200
    payload = response.get_json()
    assert 'products' in payload
    assert isinstance(payload['products'], list)


def test_order_creation_calculates_subtotal_and_reference():
    app = create_app()
    client = app.test_client()

    response = client.post(
        '/api/orders',
        json={
            'items': [
                {'product_id': 1, 'name': 'Fresh Whole Tilapia', 'price': 650, 'quantity': 2},
                {'product_id': 2, 'name': 'Fresh Juice', 'price': 250, 'quantity': 1},
            ],
            'delivery_area': 'Langata',
            'customer': {'name': 'Jane', 'phone': '+254700000001'},
        },
    )

    assert response.status_code == 201
    payload = response.get_json()['order']
    assert payload['subtotal'] == 1550
    assert payload['delivery_area'] == 'Langata'
    assert 'order_number' in payload
    assert payload['status'] == 'PENDING_CONFIRMATION'


def test_hero_and_offer_endpoints_expose_content():
    app = create_app()
    client = app.test_client()

    hero_response = client.get('/api/content/hero')
    offers_response = client.get('/api/offers')

    assert hero_response.status_code == 200
    assert 'hero' in hero_response.get_json()
    assert offers_response.status_code == 200
    assert isinstance(offers_response.get_json()['offers'], list)


def test_shop_categories_have_at_least_three_purchasable_products_and_hero_rotation():
    app = create_app()
    client = app.test_client()

    products = client.get('/api/products').get_json()['products']
    for category in ('Fish Butchery', 'Combos', 'Kitchen', 'Drinks'):
        category_products = [product for product in products if product['category'] == category]
        assert len(category_products) >= 3
        assert all(not product['demo_only'] for product in category_products)
        assert all(product['price'] > 0 and product['image_url'] and product['stock_quantity'] > 0 for product in category_products)
        assert len({product['id'] for product in category_products}) == len(category_products)

    slides = client.get('/api/content/hero').get_json()['slides']
    assert len(slides) >= 6
    assert len({slide['image_url'] for slide in slides}) >= 6


def test_seeded_category_products_can_be_ordered():
    app = create_app()
    client = app.test_client()
    product = next(
        product for product in client.get('/api/products').get_json()['products']
        if product['category'] == 'Combos'
    )

    response = client.post(
        '/api/orders',
        json={
            'items': [{'product_id': product['id'], 'quantity': 1}],
            'customer': {'name': 'Jane Doe', 'phone': '+254700000001'},
        },
    )

    assert response.status_code == 201
    assert response.get_json()['order']['items'][0]['product_name'] == product['name']


def test_admin_login_requires_valid_credentials():
    app = create_app()
    client = app.test_client()

    bad_response = client.post('/api/auth/login', json={'email': 'wrong@example.com', 'password': 'badpass'})
    assert bad_response.status_code == 403

    os.environ['ADMIN_PROVISION_TOKEN'] = 'test-provision-secret'
    provision = client.post('/api/auth/provision-admin', headers={'X-Admin-Provision-Token': 'test-provision-secret'}, json={
        'email': 'ian@gmail.com',
        'password': 'ChangeMe123!',
        'full_name': 'Ian',
    })
    assert provision.status_code == 201
    good_response = client.post('/api/auth/login', json={'email': 'ian@gmail.com', 'password': 'ChangeMe123!'})
    assert good_response.status_code == 200
    payload = good_response.get_json()
    assert 'token' in payload


def test_product_detail_endpoint_uses_database_id():
    app = create_app()
    client = app.test_client()

    response = client.get('/api/products/1')
    assert response.status_code == 200
    payload = response.get_json()['product']
    assert payload['id'] == 1
    assert 'name' in payload


def test_order_reduces_stock_and_blocks_over_quantity():
    app = create_app()
    client = app.test_client()

    product_response = client.get('/api/products/1')
    product_before = product_response.get_json()['product']['stock_quantity']

    order_response = client.post(
        '/api/orders',
        json={
            'items': [{'product_id': 1, 'quantity': 2, 'price': 650}],
            'customer': {'name': 'Jane Doe', 'phone': '+254700000001'},
        },
    )
    assert order_response.status_code == 201

    updated_product = client.get('/api/products/1').get_json()['product']
    assert updated_product['stock_quantity'] == product_before - 2

    blocked_response = client.post(
        '/api/orders',
        json={
            'items': [{'product_id': 1, 'quantity': 999, 'price': 650}],
            'customer': {'name': 'Jane Doe', 'phone': '+254700000001'},
        },
    )
    assert blocked_response.status_code == 400


def test_admin_sales_report_requires_authentication():
    app = create_app()
    client = app.test_client()

    response = client.get('/api/admin/reports/sales')
    assert response.status_code == 401


def test_admin_can_assign_kitchen_serving_sizes():
    app = create_app()
    client = app.test_client()

    os.environ['ADMIN_PROVISION_TOKEN'] = 'test-provision-secret'
    client.post('/api/auth/provision-admin', headers={'X-Admin-Provision-Token': 'test-provision-secret'}, json={
        'email': 'ian@gmail.com',
        'password': 'ChangeMe123!',
    })
    login = client.post('/api/auth/login', json={
        'email': 'ian@gmail.com',
        'password': 'ChangeMe123!',
    })
    token = login.get_json()['token']
    headers = {'Authorization': f'Bearer {token}'}

    response = client.post('/api/products', headers=headers, json={
        'sku': 'TEST-KITCHEN-1',
        'name': 'Test Family Meal',
        'description': 'A test kitchen menu item.',
        'category': 'Kitchen',
        'selling_price': 900,
        'unit': 'per platter',
        'stock_quantity': 5,
        'is_available': True,
        'featured': True,
        'status': 'Active',
        'serving_sizes': ['2–3 People', '4–5 People'],
    })
    assert response.status_code == 201
    product = response.get_json()['product']
    assert product['serving_sizes'] == ['2–3 People', '4–5 People']
    assert product['featured'] is True


def test_order_tracking_returns_sanitized_order_and_generated_tracking_number():
    app = create_app()
    client = app.test_client()
    created = client.post('/api/orders', json={
        'idempotency_key': 'frontend-tracking-test',
        'items': [{'product_id': 1, 'quantity': 1, 'price': 650}],
        'customer': {'name': 'Private Customer', 'phone': '+254700000001'},
    })
    assert created.status_code == 201
    order = created.get_json()['order']
    tracking_number = order['tracking_number']
    assert tracking_number.startswith('PAZ-')

    tracked = client.get(f'/api/orders/tracking/{tracking_number}')
    assert tracked.status_code == 200
    payload = tracked.get_json()['order']
    assert payload['tracking_number'] == tracking_number
    assert 'customer_name' not in payload
    assert 'customer_phone' not in payload
    assert payload['items']
