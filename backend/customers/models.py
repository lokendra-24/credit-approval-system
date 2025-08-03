from django.db import models

class Customer(models.Model):
    first_name = models.CharField(max_length=60)
    last_name = models.CharField(max_length=60)
    age = models.PositiveIntegerField()
    monthly_income = models.PositiveIntegerField()
    phone_number = models.CharField(max_length=15, unique=True)

    approved_limit = models.PositiveIntegerField(default=0)
    current_debt = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.phone_number})"
