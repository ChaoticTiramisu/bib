from locust import HttpUser, task, between
from datetime import datetime, timedelta
import random

class BibliotheekUser(HttpUser):
    wait_time = between(1, 3)  # Random wait between tasks

    def on_start(self):
        """Log in before starting the tasks"""
        self.login()
        self.ISBN_list = [
            "5434567",  # Replace with actual ISBNs from your database
            "7943029",
            "7656789"
        ]

    def login(self):
        """Simulate user login"""
        response = self.client.post("/login", {
            "login_email": "admin@example.com",  # Replace with valid test account
            "login_paswoord": "admin123"
        })
        if response.status_code != 200:
            print("Login failed:", response.status_code)

    @task(2)
    def view_homepage(self):
        self.client.get("/")

    @task(3)
    def search_books(self):
        search_terms = ["python", "javascript", "web", "database"]
        self.client.get(f"/search?q={random.choice(search_terms)}")

    @task(1)
    def view_book_details(self):
        isbn = random.choice(self.ISBN_list)
        self.client.get(f"/boek/{isbn}")

    @task(1)
    def reserve_book(self):
        isbn = random.choice(self.ISBN_list)
        start_date = (datetime.now() + timedelta(days=random.randint(1, 30))).strftime('%Y-%m-%d')
        end_date = (datetime.now() + timedelta(days=random.randint(31, 90))).strftime('%Y-%m-%d')

        self.client.post(f"/boek/{isbn}/reserveer", {
            "start_date": start_date,
            "end_date": end_date
        })

    @task(1)
    def view_overdue(self):
        self.client.get("/admin/overdue")
