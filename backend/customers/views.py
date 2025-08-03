from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Customer
from .serializers import RegisterCustomerSerializer, CustomerResponseSerializer

def round_to_nearest_lakh(amount: int) -> int:
    LAKH = 100_000
    return int(round(amount / LAKH)) * LAKH

class RegisterCustomerView(APIView):
    def post(self, request):
        ser = RegisterCustomerSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        monthly_income = int(data["monthly_income"])
        approved_limit = round_to_nearest_lakh(36 * monthly_income)

        customer = Customer.objects.create(
            first_name=data["first_name"],
            last_name=data["last_name"],
            age=data["age"],
            monthly_income=monthly_income,
            phone_number=data["phone_number"],
            approved_limit=approved_limit,
        )
        return Response(CustomerResponseSerializer(customer).data, status=status.HTTP_201_CREATED)

from .tasks import ingest_initial_data

class IngestInitialDataView(APIView):
    """
    POST /ingest-data
    Triggers Celery background task to read Excel files in /data/
    """
    def post(self, request):
        task = ingest_initial_data.delay()
        return Response({"task_id": task.id, "status": "started"})

