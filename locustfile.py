from locust import HttpUser, task, between


class ReserveUser(HttpUser):
    wait_time = between(1, 2)

    @task
    def reserve_product(self):
        self.client.post(
            "/reserve",
            json={
                "product_id": "iphone",
                "quantity": 1
            }
        )