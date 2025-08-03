from rest_framework import serializers
from decimal import Decimal
from .models import Loan
from customers.models import Customer

class EligibilityRequestSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField()
    loan_amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal('0.01'))
    interest_rate = serializers.DecimalField(max_digits=5, decimal_places=2, min_value=Decimal('0.01'))
    tenure = serializers.IntegerField(min_value=1, max_value=600)  # max 50 years

class EligibilityResponseSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField()
    approval = serializers.BooleanField()
    interest_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    corrected_interest_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    tenure = serializers.IntegerField()
    monthly_installment = serializers.DecimalField(max_digits=12, decimal_places=2)

class LoanListSerializer(serializers.ModelSerializer):
    """Optimized serializer for loan list views with minimal fields"""
    customer_name = serializers.CharField(source='customer.first_name', read_only=True)
    
    class Meta:
        model = Loan
        fields = ['id', 'customer_name', 'loan_amount', 'tenure', 'interest_rate', 'start_date', 'end_date']

class LoanDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for individual loan views"""
    customer = serializers.StringRelatedField()
    
    class Meta:
        model = Loan
        fields = '__all__'
