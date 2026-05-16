import concurrent.futures
import requests

BASE_URL = "http://localhost:8002"


def reset_stock(product_id: str, stock: int):
    response = requests.post(
        f"{BASE_URL}/reset-stock",
        json={
            "product_id": product_id,
            "stock": stock
        },
        timeout=3
    )
    assert response.status_code == 200


def reserve(product_id: str, quantity: int):
    return requests.post(
        f"{BASE_URL}/reserve",
        json={
            "product_id": product_id,
            "quantity": quantity
        },
        timeout=3
    )


def get_stock(product_id: str):
    response = requests.get(f"{BASE_URL}/stock", timeout=3)
    assert response.status_code == 200
    stock = response.json()
    return int(stock[product_id])


def test_dos_usuarios_un_producto():
    reset_stock("iphone", 1)

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(reserve, "iphone", 1),
            executor.submit(reserve, "iphone", 1)
        ]

        responses = [f.result() for f in futures]

    success = [r for r in responses if r.status_code == 200]
    rejected = [r for r in responses if r.status_code in [400, 503]]

    assert len(success) == 1
    assert len(rejected) == 1
    assert get_stock("iphone") == 0


def test_cincuenta_usuarios_diez_productos():
    reset_stock("iphone", 10)

    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        futures = [
            executor.submit(reserve, "iphone", 1)
            for _ in range(50)
        ]

        responses = [f.result() for f in futures]

    success = [r for r in responses if r.status_code == 200]
    rejected = [r for r in responses if r.status_code in [400, 503]]

    assert len(success) == 10
    assert len(rejected) == 40
    assert get_stock("iphone") == 0


def test_redis_no_se_cuelga():
    response = requests.post(
        f"{BASE_URL}/reserve",
        json={
            "product_id": "iphone",
            "quantity": 1
        },
        timeout=3
    )

    assert response.status_code in [200, 400, 503]