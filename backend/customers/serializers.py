from rest_framework import serializers
from .models import Customer

class RegisterCustomerSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=60)
    last_name = serializers.CharField(max_length=60)
    age = serializers.IntegerField(min_value=18)
    monthly_income = serializers.IntegerField(min_value=0)
    phone_number = serializers.CharField(max_length=15)

class CustomerResponseSerializer(serializers.ModelSerializer):
    customer_id = serializers.IntegerField(source="id", read_only=True)
    name = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = ["customer_id", "name", "age", "monthly_income", "approved_limit", "phone_number"]

    def get_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()
