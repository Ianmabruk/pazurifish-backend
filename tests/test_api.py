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


def test_admin_login_requires_valid_credentials():
    app = create_app()
    client = app.test_client()

    bad_response = client.post('/api/auth/login', json={'email': 'wrong@example.com', 'password': 'badpass'})
    assert bad_response.status_code == 401

    good_response = client.post('/api/auth/login', json={'email': 'admin@pazurifish.local', 'password': 'ChangeMe123!'})
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
