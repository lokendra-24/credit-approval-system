from decimal import Decimal
from django.test import SimpleTestCase
from loans.views import monthly_emi, enforce_interest_slab

class EmiAndSlabTests(SimpleTestCase):
    def test_monthly_emi_zero_rate(self):
        self.assertEqual(monthly_emi(Decimal("12000"), Decimal("0"), 12), Decimal("1000.00"))

    def test_monthly_emi_positive_rate(self):
        self.assertEqual(monthly_emi(Decimal("250000"), Decimal("12"), 24), Decimal("11768.37"))

    def test_slab_gt50(self):
        ok, rate = enforce_interest_slab(80, 10.0)
        self.assertTrue(ok); self.assertEqual(rate, 10.0)

    def test_slab_31to50(self):
        ok, rate = enforce_interest_slab(45, 10.0)
        self.assertTrue(ok); self.assertEqual(rate, 12.0)

    def test_slab_11to30(self):
        ok, rate = enforce_interest_slab(25, 12.0)
        self.assertTrue(ok); self.assertEqual(rate, 16.0)

    def test_slab_le10(self):
        ok, rate = enforce_interest_slab(10, 20.0)
        self.assertFalse(ok); self.assertEqual(rate, 20.0)
