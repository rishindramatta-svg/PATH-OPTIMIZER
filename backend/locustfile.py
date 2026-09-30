import os

from locust import HttpUser, between, task


class PNG9Learner(HttpUser):
    wait_time = between(0.05, 0.2)

    def on_start(self):
        response = self.client.post(
            "/api/auth/login",
            json={
                "email": os.getenv("LOAD_TEST_EMAIL", "student@png9.local"),
                "password": os.getenv("LOAD_TEST_PASSWORD", "DemoPass123!"),
            },
            name="POST /api/auth/login",
        )
        if response.status_code != 200:
            response.failure(f"Login failed: {response.status_code}")

    @task(5)
    def answer_question(self):
        response = self.client.get("/api/questions/next", name="GET /api/questions/next")
        if response.status_code != 200:
            return
        question = response.json()
        self.client.post(
            "/api/interactions",
            json={
                "questionId": question["id"],
                "answer": "0",
                "confidence": 4,
                "timeTakenMs": 4000,
                "sessionId": question["sessionId"],
            },
            name="POST /api/interactions",
        )

    @task(3)
    def read_path(self):
        self.client.get("/api/path", name="GET /api/path")

    @task(2)
    def read_analytics(self):
        self.client.get("/api/analytics?period=30d", name="GET /api/analytics")
