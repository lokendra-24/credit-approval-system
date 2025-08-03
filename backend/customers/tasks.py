from __future__ import annotations
import pandas as pd
from decimal import Decimal
from celery import shared_task
from django.db import transaction
from datetime import datetime, timedelta

from customers.models import Customer
from loans.models import Loan


# ----------------- Helpers -----------------

def _norm(s: str) -> str:
    """Normalize a header key: lowercase + only alnum (removes spaces/underscores)."""
    return "".join(ch for ch in str(s).lower() if ch.isalnum())

def _map_cols(df: pd.DataFrame) -> dict[str, str]:
    """Map normalized header -> original header name present in DataFrame."""
    return {_norm(c): c for c in df.columns}

def _get(row, cols_map: dict[str, str], name: str, default=None):
    """Get row value for a logical header name regardless of spaces/underscores/case."""
    key = _norm(name)
    if key in cols_map:
        return row[cols_map[key]]
    return default

def _parse_date(val):
    if pd.isna(val) or val in ("", None):
        return None
    if isinstance(val, datetime):
        return val.date()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(str(val), fmt).date()
        except Exception:
            pass
    try:
        return pd.to_datetime(val).date()
    except Exception:
        return None

def _monthly_emi(principal: Decimal, annual_rate_pct: Decimal, months: int) -> Decimal:
    """Compound-interest EMI (monthly) — used if sheet EMI missing/zero."""
    if months <= 0:
        return Decimal("0.00")
    P = Decimal(principal or 0)
    r = (Decimal(annual_rate_pct or 0) / Decimal("100")) / Decimal("12")
    if r == 0:
        return (P / Decimal(months)).quantize(Decimal("0.01"))
    one_plus_r_pow_n = (Decimal("1") + r) ** Decimal(months)
    emi = P * r * one_plus_r_pow_n / (one_plus_r_pow_n - Decimal("1"))
    return emi.quantize(Decimal("0.01"))


# ----------------- Task -----------------

@shared_task
def ingest_initial_data(
    customer_xlsx_path: str = "/data/customer_data.xlsx",
    loan_xlsx_path: str = "/data/loan_data.xlsx",
) -> dict:
    """
    Ingest customers and loans from Excel.
    - Preserves provided IDs (customer id, loan id) when present.
    - Normalizes header names (spaces/underscores/case don’t matter).
    - Computes EMI if missing in loans sheet.
    """
    created_customers = 0
    updated_customers = 0
    created_loans = 0
    updated_loans = 0
    errors: list[str] = []

    # ---------- Customers ----------
    try:
        cdf = pd.read_excel(customer_xlsx_path)
    except Exception as e:
        errors.append(f"Failed to read customers Excel: {e}")
        cdf = pd.DataFrame()

    cust_cols = _map_cols(cdf) if not cdf.empty else {}

    # Expected logical fields (any header spelling works):
    # customer id / customer_id
    # first name / first_name
    # last name / last_name
    # phone number / phone_number
    # monthly salary / monthly_income
    # approved limit / approved_limit
    # current debt / current_debt
    # (age not in sheet -> default 30)
    
    # Batch process customers for better performance
    customers_to_create = []
    customers_to_update = []
    
    with transaction.atomic():
        for _, row in cdf.iterrows():
            try:
                pk = _get(row, cust_cols, "customer_id")
                first_name = (_get(row, cust_cols, "first_name", "") or "").strip()
                last_name = (_get(row, cust_cols, "last_name", "") or "").strip()
                phone_number = str(_get(row, cust_cols, "phone_number", "") or "").strip()

                monthly_salary = _get(row, cust_cols, "monthly_salary")
                if monthly_salary is None:
                    monthly_salary = _get(row, cust_cols, "monthly_income", 0)
                monthly_salary = int(monthly_salary or 0)

                approved_limit = int(_get(row, cust_cols, "approved_limit", 0) or 0)
                current_debt = Decimal(str(_get(row, cust_cols, "current_debt", 0) or 0))
                age = int(_get(row, cust_cols, "age", 30) or 30)

                if pd.notna(pk):
                    pk = int(pk)
                    _, created = Customer.objects.update_or_create(
                        id=pk,
                        defaults=dict(
                            first_name=first_name,
                            last_name=last_name,
                            age=age,
                            monthly_income=monthly_salary,
                            phone_number=phone_number,
                            approved_limit=approved_limit,
                            current_debt=current_debt,
                        ),
                    )
                else:
                    _, created = Customer.objects.update_or_create(
                        phone_number=phone_number,
                        defaults=dict(
                            first_name=first_name,
                            last_name=last_name,
                            age=age,
                            monthly_income=monthly_salary,
                            approved_limit=approved_limit,
                            current_debt=current_debt,
                        ),
                    )

                if created:
                    created_customers += 1
                else:
                    updated_customers += 1

            except Exception as e:
                errors.append(f"Customer row error: {e}")
        
        # Use bulk operations for better performance
        if customers_to_create:
            Customer.objects.bulk_create(customers_to_create, batch_size=1000, ignore_conflicts=True)
            created_customers += len(customers_to_create)

    # ---------- Loans ----------
    try:
        ldf = pd.read_excel(loan_xlsx_path)
    except Exception as e:
        errors.append(f"Failed to read loans Excel: {e}")
        ldf = pd.DataFrame()

    loan_cols = _map_cols(ldf) if not ldf.empty else {}

    # Expected logical fields:
    # customer id, loan id, loan amount, tenure, interest rate,
    # monthly repayment (emi), EMIs paid on time, start date, end date
    with transaction.atomic():
        for _, row in ldf.iterrows():
            try:
                cust_id = _get(row, loan_cols, "customer_id")
                loan_id = _get(row, loan_cols, "loan_id")

                if pd.isna(cust_id):
                    errors.append("Loan row skipped: missing customer id")
                    continue
                cust_id = int(cust_id)

                try:
                    customer = Customer.objects.get(id=cust_id)
                except Customer.DoesNotExist:
                    errors.append(f"Loan row skipped: customer {cust_id} not found")
                    continue

                loan_amount = Decimal(str(_get(row, loan_cols, "loan_amount", 0) or 0))
                tenure = int(_get(row, loan_cols, "tenure", 0) or 0)
                interest_rate = Decimal(str(_get(row, loan_cols, "interestrate", 0) or 0))

                # EMI header may be 'monthly repayment (emi)' or just 'emi'
                emi = _get(row, loan_cols, "monthlyrepaymentemi")
                if emi is None:
                    emi = _get(row, loan_cols, "emi")
                emi = Decimal(str(emi or 0))

                emis_paid_on_time = int(_get(row, loan_cols, "emispaidontime", 0) or 0)
                start_date = _parse_date(_get(row, loan_cols, "startdate"))
                end_date = _parse_date(_get(row, loan_cols, "enddate"))

                # Fallback if start_date missing but end_date & tenure available
                if start_date is None and end_date is not None and tenure > 0:
                    start_date = end_date - timedelta(days=30 * tenure)

                # If both dates missing, skip cleanly (avoid DB NOT NULL error)
                if start_date is None and end_date is None:
                    errors.append(f"Loan row skipped: both start_date and end_date missing for customer {cust_id}")
                    continue

                # Compute EMI if not provided
                if emi == 0 and loan_amount > 0 and tenure > 0:
                    emi = _monthly_emi(loan_amount, interest_rate, tenure)

                if pd.notna(loan_id):
                    loan_id = int(loan_id)
                    _, created = Loan.objects.update_or_create(
                        id=loan_id,
                        defaults=dict(
                            customer=customer,
                            loan_amount=loan_amount,
                            tenure=tenure,
                            interest_rate=interest_rate,
                            monthly_installment=emi,
                            emis_paid_on_time=emis_paid_on_time,
                            start_date=start_date,
                            end_date=end_date,
                        ),
                    )
                else:
                    _, created = Loan.objects.update_or_create(
                        customer=customer,
                        loan_amount=loan_amount,
                        tenure=tenure,
                        interest_rate=interest_rate,
                        start_date=start_date,
                        end_date=end_date,
                        defaults=dict(
                            monthly_installment=emi,
                            emis_paid_on_time=emis_paid_on_time,
                        ),
                    )

                if created:
                    created_loans += 1
                else:
                    updated_loans += 1

            except Exception as e:
                errors.append(f"Loan row error: {e}")

    return {
        "customers": {"created": created_customers, "updated": updated_customers},
        "loans": {"created": created_loans, "updated": updated_loans},
        "errors": errors,
    }
