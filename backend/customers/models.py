from django.db import models

class Customer(models.Model):
    first_name = models.CharField(max_length=60)
    last_name = models.CharField(max_length=60)
    age = models.PositiveIntegerField()
    monthly_income = models.PositiveIntegerField()
    phone_number = models.CharField(max_length=15, unique=True, db_index=True)

    approved_limit = models.PositiveIntegerField(default=0, db_index=True)
    current_debt = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['monthly_income', 'approved_limit']),
            models.Index(fields=['created_at']),
            models.Index(fields=['first_name', 'last_name']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.phone_number})"
