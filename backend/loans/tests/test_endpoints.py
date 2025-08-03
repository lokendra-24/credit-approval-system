import json
from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from customers.models import Customer
from loans.models import Loan

class EndpointTests(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(
            first_name="Test", last_name="User", age=30,
            monthly_income=60000, phone_number="9999999999",
            approved_limit=2200000, current_debt=Decimal("0"),
        )

    def test_register(self):
        url = "/register"
        body = {
            "first_name": "Amit", "last_name": "Kumar",
            "age": 28, "monthly_income": 60000, "phone_number": "9876543210"
        }
        resp = self.client.post(url, data=json.dumps(body),
                                content_type="application/json")
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertIn("approved_limit", data)
        self.assertEqual(data["approved_limit"], 2200000)

    def test_check_eligibility(self):
        url = "/check-eligibility"
        payload = {
            "customer_id": self.customer.id,
            "loan_amount": 250000,
            "interest_rate": 12.0,
            "tenure": 24
        }
        resp = self.client.post(url, data=json.dumps(payload),
                                content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("approval", data)
        self.assertIn("monthly_installment", data)

    def test_create_and_view_loan(self):
        # create
        create_url = "/create-loan"
        payload = {
            "customer_id": self.customer.id,
            "loan_amount": 250000,
            "interest_rate": 12.0,
            "tenure": 24
        }
        r = self.client.post(create_url, data=json.dumps(payload),
                             content_type="application/json")
        self.assertIn(r.status_code, (200, 201))
        loan_id = r.json().get("loan_id")
        self.assertTrue(loan_id)

        # view single
        view_one = f"/view-loan/{loan_id}"
        r1 = self.client.get(view_one)
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r1.json()["loan_id"], loan_id)

        # view all for customer
        view_all = f"/view-loans/{self.customer.id}"
        r2 = self.client.get(view_all)
        self.assertEqual(r2.status_code, 200)
        self.assertIsInstance(r2.json(), list)
