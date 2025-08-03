from django.db import models
from customers.models import Customer

class Loan(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="loans", db_index=True)
    loan_amount = models.DecimalField(max_digits=12, decimal_places=2, db_index=True)
    tenure = models.PositiveIntegerField(help_text="months")
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    monthly_installment = models.DecimalField(max_digits=12, decimal_places=2)
    emis_paid_on_time = models.PositiveIntegerField(default=0)
    start_date = models.DateField(db_index=True)
    end_date = models.DateField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['customer', 'end_date']),
            models.Index(fields=['customer', 'start_date']),
            models.Index(fields=['start_date', 'end_date']),
            models.Index(fields=['customer', 'created_at']),
        ]
        ordering = ['-created_at']
        
    def __str__(self):
        return f"Loan {self.id} for {self.customer} - {self.loan_amount}"
