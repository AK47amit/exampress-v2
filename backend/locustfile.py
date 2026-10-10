import os
from locust import HttpUser, task, between

class ExampressSaaSUser(HttpUser):
    """
    Simulates concurrent enterprise users registering, logging in, 
    checking health status, and triggering book generation workflows.
    """
    wait_time = between(1, 3)  # Wait 1 to 3 seconds between tasks
    token = None

    def on_start(self):
        """Setup test user and fetch JWT token before running tasks."""
        self.email = "loadtest_user@exampur.com"
        self.password = "securepassword123"
        
        # Try registering test user (ignore if already registered)
        self.client.post("/api/v2/auth/register", json={
            "email": self.email,
            "password": self.password
        }, catch_response=True)

        # Login to get JWT Bearer token
        response = self.client.post("/api/v2/auth/login", data={
            "username": self.email,
            "password": self.password
        })
        
        if response.status_code == 200:
            self.token = response.json().get("access_token")

    @task(3)
    def test_health_check(self):
        """Hit the main health check endpoint frequently."""
        self.client.get("/")

    @task(2)
    def test_get_projects(self):
        """Simulate users viewing their saved projects vault."""
        if self.token:
            headers = {"Authorization": f"Bearer {self.token}"}
            self.client.get("/api/v2/projects", headers=headers)

    @task(1)
    def test_generate_async_book(self):
        """Simulate heavy asynchronous book generation queueing."""
        if self.token:
            headers = {"Authorization": f"Bearer {self.token}"}
            self.client.post("/api/v2/generate-async", data={
                "book_type": "quiz",
                "format_size": "B5",
                "column_count": 2
            }, headers=headers)