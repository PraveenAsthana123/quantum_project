"""Locust load test — quantum portal API.
Run: locust -f scripts/load_test.py --host=http://localhost:8001 --users=10 --spawn-rate=2 --run-time=60s --headless
Target: p95 metadata API <500ms, <1% failure rate, 10 concurrent users
"""
from locust import HttpUser, task, between

class QuantumAPIUser(HttpUser):
    wait_time = between(1, 3)

    @task(5)
    def get_projects(self):
        self.client.get("/projects")

    @task(3)
    def get_project_detail(self):
        self.client.get("/projects/qc-banking-lab")

    @task(2)
    def get_health(self):
        self.client.get("/health")

    @task(2)
    def get_layers(self):
        self.client.get("/layers")

    @task(1)
    def get_reports(self):
        self.client.get("/reports/summary")

    @task(1)
    def get_analytics(self):
        self.client.get("/analytics/summary")
