# Credit Approval System - API Testing Guide

This guide provides comprehensive examples for testing all API endpoints of the Credit Approval System.

## Prerequisites

- Django server running on `http://localhost:8000`
- Sample data loaded (use `/ingest-data` endpoint)

## API Endpoints Overview

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/register` | POST | Register a new customer |
| `/check-eligibility` | POST | Check loan eligibility |
| `/create-loan` | POST | Create a new loan |
| `/view-loan/{loan_id}` | GET | View loan details |
| `/view-loans/{customer_id}` | GET | View customer's loans |
| `/ingest-data` | POST | Load sample data |

## 1. Data Ingestion

First, load the sample data:

```bash
curl -X POST http://localhost:8000/ingest-data \
  -H "Content-Type: application/json"
```

**Expected Response:**
```json
{
  "task_id": "abc123...",
  "status": "started"
}
```

## 2. Customer Registration

Register a new customer:

```bash
curl -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Alice",
    "last_name": "Johnson",
    "age": 28,
    "monthly_income": 75000,
    "phone_number": "9876543999"
  }'
```

**Expected Response:**
```json
{
  "customer_id": 6,
  "name": "Alice Johnson",
  "age": 28,
  "monthly_income": 75000,
  "approved_limit": 2700000,
  "phone_number": "9876543999"
}
```

**Key Points:**
- `approved_limit` = 36 × `monthly_income` (rounded to nearest lakh)
- Phone number must be unique
- All fields are required

## 3. Check Loan Eligibility

Check if a customer is eligible for a loan:

```bash
curl -X POST http://localhost:8000/check-eligibility \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": 1,
    "loan_amount": 500000,
    "interest_rate": 10.5,
    "tenure": 24
  }'
```

**Expected Response:**
```json
{
  "customer_id": 1,
  "approval": true,
  "interest_rate": 10.5,
  "corrected_interest_rate": 10.5,
  "tenure": 24,
  "monthly_installment": 23026.69
}
```

**Credit Score Rules:**
- **Score > 50**: Approve at requested rate
- **30 < Score ≤ 50**: Approve with minimum 12% interest
- **10 < Score ≤ 30**: Approve with minimum 16% interest
- **Score ≤ 10**: Reject loan

**Additional Rules:**
- If current loans > approved limit → Credit score = 0
- If total EMIs > 50% of monthly salary → Reject loan

## 4. Create Loan

Create a new loan (must pass eligibility check):

```bash
curl -X POST http://localhost:8000/create-loan \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": 1,
    "loan_amount": 500000,
    "interest_rate": 10.5,
    "tenure": 24
  }'
```

**Expected Response (Approved):**
```json
{
  "loan_id": 10,
  "customer_id": 1,
  "loan_approved": true,
  "message": "Loan approved",
  "monthly_installment": 23026.69
}
```

**Expected Response (Rejected):**
```json
{
  "loan_id": null,
  "customer_id": 1,
  "loan_approved": false,
  "message": "Loan not approved based on credit rules/affordability.",
  "monthly_installment": 23026.69
}
```

## 5. View Loan Details

Get detailed information about a specific loan:

```bash
curl -X GET http://localhost:8000/view-loan/1
```

**Expected Response:**
```json
{
  "loan_id": 1,
  "customer": {
    "id": 1,
    "first_name": "John",
    "last_name": "Doe",
    "phone_number": "9876543210",
    "age": 30
  },
  "loan_amount": 500000.0,
  "interest_rate": 10.5,
  "monthly_installment": 23026.69,
  "tenure": 24
}
```

## 6. View Customer Loans

Get all current loans for a customer:

```bash
curl -X GET http://localhost:8000/view-loans/1
```

**Expected Response:**
```json
[
  {
    "loan_id": 1,
    "loan_amount": 500000.0,
    "interest_rate": 10.5,
    "monthly_installment": 23026.69,
    "repayments_left": 18
  },
  {
    "loan_id": 2,
    "loan_amount": 300000.0,
    "interest_rate": 9.5,
    "monthly_installment": 26158.87,
    "repayments_left": 6
  }
]
```

## Testing Scenarios

### Scenario 1: High Credit Score Customer
```bash
# Customer with good payment history (Customer ID: 1)
curl -X POST http://localhost:8000/check-eligibility \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": 1,
    "loan_amount": 200000,
    "interest_rate": 8.0,
    "tenure": 12
  }'
```
Expected: Approval at requested rate (8.0%)

### Scenario 2: Medium Credit Score Customer
```bash
# Customer with mixed payment history (Customer ID: 2)
curl -X POST http://localhost:8000/check-eligibility \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": 2,
    "loan_amount": 300000,
    "interest_rate": 10.0,
    "tenure": 18
  }'
```
Expected: Approval with corrected rate (≥12%)

### Scenario 3: Low Credit Score Customer
```bash
# Customer with poor payment history (Customer ID: 3)
curl -X POST http://localhost:8000/check-eligibility \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": 3,
    "loan_amount": 100000,
    "interest_rate": 12.0,
    "tenure": 12
  }'
```
Expected: Approval with corrected rate (≥16%)

### Scenario 4: Affordability Check
```bash
# Large loan amount that exceeds 50% of salary
curl -X POST http://localhost:8000/check-eligibility \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": 4,
    "loan_amount": 1000000,
    "interest_rate": 10.0,
    "tenure": 12
  }'
```
Expected: Rejection due to affordability

## Error Handling

### Invalid Customer ID
```bash
curl -X POST http://localhost:8000/check-eligibility \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": 999,
    "loan_amount": 100000,
    "interest_rate": 10.0,
    "tenure": 12
  }'
```
Expected: 404 Not Found

### Invalid Loan ID
```bash
curl -X GET http://localhost:8000/view-loan/999
```
Expected: 404 Not Found

### Missing Required Fields
```bash
curl -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "John"
  }'
```
Expected: 400 Bad Request with validation errors

## Credit Scoring Details

The system calculates credit scores (0-100) based on:

1. **Payment History (40 points)**: Ratio of EMIs paid on time
2. **Number of Loans (15 points)**: Fewer loans = better score
3. **Current Year Activity (15 points)**: Less activity = better score
4. **Loan Volume vs Limit (30 points)**: Lower utilization = better score

### Special Rules:
- If current loans > approved limit → Credit score = 0
- If total EMIs > 50% of monthly salary → Reject loan

## Sample Data Overview

The system includes sample data with 5 customers and 9 loans:

- **Customer 1**: Excellent payment history (Score: ~85)
- **Customer 2**: Good payment history (Score: ~65)
- **Customer 3**: Poor payment history (Score: ~25)
- **Customer 4**: New customer (Score: ~60)
- **Customer 5**: Multiple loans, good history (Score: ~75)

## Performance Testing

For load testing, you can use tools like Apache Bench:

```bash
# Test customer registration endpoint
ab -n 100 -c 10 -T 'application/json' \
  -p register_data.json \
  http://localhost:8000/register

# Test eligibility check endpoint
ab -n 100 -c 10 -T 'application/json' \
  -p eligibility_data.json \
  http://localhost:8000/check-eligibility
```

## Troubleshooting

### Common Issues:

1. **CSRF Token Error**: Ensure CSRF middleware is disabled for API endpoints
2. **Database Connection**: Check PostgreSQL/SQLite database configuration
3. **Data Not Found**: Run data ingestion endpoint first
4. **Unique Constraint**: Use unique phone numbers for customer registration

### Debug Mode:
Set `DEBUG=True` in settings for detailed error messages during development.

## Production Considerations

1. **Enable CSRF Protection**: Re-enable CSRF middleware for production
2. **Authentication**: Add proper authentication for API endpoints
3. **Rate Limiting**: Implement rate limiting for API endpoints
4. **Logging**: Add comprehensive logging for all API operations
5. **Monitoring**: Set up monitoring for API performance and errors