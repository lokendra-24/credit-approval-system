# backend/customers/urls.py
from django.urls import path
from .views import RegisterCustomerView, IngestInitialDataView

urlpatterns = [
    path("register", RegisterCustomerView.as_view(), name="register"),
    path("ingest-data", IngestInitialDataView.as_view(), name="ingest-data"),
]
