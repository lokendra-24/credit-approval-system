from datetime import date, timedelta
from decimal import Decimal
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response

from customers.models import Customer
from .models import Loan
from .serializers import (
    EligibilityRequestSerializer, EligibilityResponseSerializer,
)

# ---------- Helpers (PDF-aligned) ----------

def monthly_emi(principal: Decimal, annual_rate_pct: Decimal, months: int) -> Decimal:
    """Compound-interest EMI (monthly compounding)."""
    if months <= 0:
        return Decimal("0.00")
    P = Decimal(principal)
    r = (Decimal(annual_rate_pct) / Decimal("100")) / Decimal("12")
    if r == 0:
        return (P / Decimal(months)).quantize(Decimal("0.01"))
    one_plus_r_pow_n = (Decimal("1") + r) ** Decimal(months)
    emi = P * r * one_plus_r_pow_n / (one_plus_r_pow_n - Decimal("1"))
    return emi.quantize(Decimal("0.01"))

def compute_credit_score(customer: Customer) -> int:
    """
    Credit score (0-100) using PDF factors:
      i.  Past EMIs paid on time
      ii. Number of loans taken in past
      iii.Loan activity in current year
      iv. Approved loan volume
      v.  If sum(current loans) > approved_limit => 0
    Heuristic weights to map to 100.
    """
    loans = Loan.objects.filter(customer=customer)
    today = date.today()

    # v) Hard stop: current principal > approved_limit -> score = 0
    current_principal = loans.filter(end_date__gte=today).aggregate(
        total=Sum("loan_amount")
    )["total"] or Decimal("0")
    if current_principal > Decimal(customer.approved_limit or 0):
        return 0

    if not loans.exists():
        # No history -> neutral-ish
        return 60

    # i) On-time EMI ratio (40 pts)
    total_tenure = loans.aggregate(t=Sum("tenure"))["t"] or 0
    total_on_time = loans.aggregate(t=Sum("emis_paid_on_time"))["t"] or 0
    on_time_ratio = (total_on_time / total_tenure) if total_tenure > 0 else 1.0
    s1 = max(0.0, min(1.0, on_time_ratio)) * 40

    # ii) Number of past loans (15 pts): fewer is slightly better
    n_loans = loans.count()
    s2 = 15 if n_loans <= 2 else 10 if n_loans <= 5 else 5

    # iii) Activity in current year (15 pts): more active -> slightly worse
    this_year = today.year
    active_this_year = loans.filter(start_date__year=this_year).count()
    s3 = max(0, 15 - active_this_year * 3)  # each new loan in year reduces 3 (min 0)

    # iv) Approved volume vs approved_limit (30 pts)
    total_volume = loans.aggregate(t=Sum("loan_amount"))["t"] or Decimal("0")
    limit = Decimal(customer.approved_limit or 1)
    ratio = total_volume / limit if limit > 0 else Decimal("1")
    if ratio <= Decimal("0.5"):
        s4 = 30
    elif ratio <= Decimal("1.0"):
        s4 = 20
    elif ratio <= Decimal("2.0"):
        s4 = 10
    else:
        s4 = 0

    score = int(round(s1 + s2 + s3 + s4))
    return max(0, min(100, score))

def enforce_interest_slab(credit_score: int, requested_rate: float) -> tuple[bool, float]:
    """
    PDF slabs:
      >50           : approve
      30 < score <= 50 : approve but require rate >= 12%
      10 < score <= 30 : approve but require rate >= 16%
      <=10          : don't approve
    Return (approval_allowed, corrected_rate)
    """
    rate = float(requested_rate)
    if credit_score > 50:
        return True, rate
    if 30 < credit_score <= 50:
        return True, max(rate, 12.0)
    if 10 < credit_score <= 30:
        return True, max(rate, 16.0)
    return False, rate

def affordability_ok(customer: Customer, new_emi: Decimal) -> bool:
    """If sum of all current EMIs > 50% of monthly salary => don't approve."""
    today = date.today()
    current_emi_sum = Loan.objects.filter(customer=customer, end_date__gte=today)\
                                  .aggregate(total=Sum("monthly_installment"))["total"] or Decimal("0")
    total = current_emi_sum + (new_emi or Decimal("0"))
    return total <= Decimal(customer.monthly_income) * Decimal("0.5")


# ---------- Endpoint ----------

class CheckEligibilityView(APIView):
    """
    POST /check-eligibility
    Body: { customer_id:int, loan_amount:float, interest_rate:float, tenure:int }
    Response (200): per PDF
    """
    def post(self, request):
        req = EligibilityRequestSerializer(data=request.data)
        req.is_valid(raise_exception=True)
        data = req.validated_data

        customer = get_object_or_404(Customer, id=data["customer_id"])
        amount = Decimal(str(data["loan_amount"]))
        tenure = int(data["tenure"])
        requested_rate = float(data["interest_rate"])

        credit = compute_credit_score(customer)

        # EMI at requested rate
        emi_requested = monthly_emi(amount, Decimal(str(requested_rate)), tenure)

        # Affordability rule (50% of salary cap)
        if not affordability_ok(customer, emi_requested):
            resp = {
                "customer_id": customer.id,
                "approval": False,
                "interest_rate": requested_rate,
                "corrected_interest_rate": requested_rate,
                "tenure": tenure,
                "monthly_installment": float(emi_requested),
            }
            return Response(EligibilityResponseSerializer(resp).data, status=200)

        # Slab & corrected rate
        allowed, corrected_rate = enforce_interest_slab(credit, requested_rate)
        emi_corrected = monthly_emi(amount, Decimal(str(corrected_rate)), tenure)

        approval = bool(allowed and credit > 10)

        resp = {
            "customer_id": customer.id,
            "approval": approval,
            "interest_rate": requested_rate,
            "corrected_interest_rate": float(corrected_rate),
            "tenure": tenure,
            "monthly_installment": float(emi_corrected),
        }
        return Response(EligibilityResponseSerializer(resp).data, status=200)
    
from datetime import date, timedelta
from .models import Loan  # (ensure this import exists at top)

class CreateLoanView(APIView):
    """
    POST /create-loan
    Body: { customer_id, loan_amount, interest_rate, tenure }
    Response: { loan_id, customer_id, loan_approved, message, monthly_installment }
    """
    def post(self, request):
        req = EligibilityRequestSerializer(data=request.data)
        req.is_valid(raise_exception=True)
        data = req.validated_data

        customer = get_object_or_404(Customer, id=data["customer_id"])
        amount = Decimal(str(data["loan_amount"]))
        tenure = int(data["tenure"])
        requested_rate = float(data["interest_rate"])

        # reuse eligibility logic
        credit = compute_credit_score(customer)
        allowed, corrected_rate = enforce_interest_slab(credit, requested_rate)
        emi = monthly_emi(amount, Decimal(str(corrected_rate)), tenure)

        # affordability check
        if not allowed or credit <= 10 or not affordability_ok(customer, emi):
            return Response({
                "loan_id": None,
                "customer_id": customer.id,
                "loan_approved": False,
                "message": "Loan not approved based on credit rules/affordability.",
                "monthly_installment": float(emi),
            }, status=200)

        # create loan
        start = date.today()
        end = start + timedelta(days=30 * tenure)

        loan = Loan.objects.create(
            customer=customer,
            loan_amount=amount,
            tenure=tenure,
            interest_rate=Decimal(str(corrected_rate)),
            monthly_installment=emi,
            start_date=start,
            end_date=end,
            emis_paid_on_time=0,
        )

        return Response({
            "loan_id": loan.id,
            "customer_id": customer.id,
            "loan_approved": True,
            "message": "Loan approved",
            "monthly_installment": float(emi),
        }, status=201)
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from datetime import date

class ViewLoanDetail(APIView):
    """
    GET /view-loan/<loan_id>
    Response fields per PDF:
      loan_id, customer{ id, first_name, last_name, phone_number, age },
      loan_amount, interest_rate, monthly_installment, tenure
    """
    def get(self, request, loan_id: int):
        loan = get_object_or_404(Loan, id=loan_id)
        data = {
            "loan_id": loan.id,
            "customer": {
                "id": loan.customer.id,
                "first_name": loan.customer.first_name,
                "last_name": loan.customer.last_name,
                "phone_number": loan.customer.phone_number,
                "age": loan.customer.age,
            },
            "loan_amount": float(loan.loan_amount),
            "interest_rate": float(loan.interest_rate),
            "monthly_installment": float(loan.monthly_installment),
            "tenure": loan.tenure,
        }
        return Response(data)


class ViewLoansByCustomer(APIView):
    """
    GET /view-loans/<customer_id>
    'current' loans => end_date >= today
    Each item: loan_id, loan_amount, interest_rate, monthly_installment, repayments_left
    """
    def get(self, request, customer_id: int):
        today = date.today()
        qs = Loan.objects.filter(customer_id=customer_id, end_date__gte=today).order_by("-created_at")
        items = []
        for loan in qs:
            repayments_left = max(int(loan.tenure) - int(loan.emis_paid_on_time or 0), 0)
            items.append({
                "loan_id": loan.id,
                "loan_amount": float(loan.loan_amount),
                "interest_rate": float(loan.interest_rate),
                "monthly_installment": float(loan.monthly_installment),
                "repayments_left": repayments_left,
            })
        return Response(items)

