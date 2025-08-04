# Credit Approval System

A Django-based credit approval system that processes loan applications based on historical customer data and credit scoring algorithms.

## Features

- **Customer Registration**: Register new customers with automatic credit limit calculation
- **Credit Scoring**: Advanced credit scoring based on payment history, loan activity, and financial behavior
- **Loan Eligibility**: Check loan eligibility with interest rate corrections based on credit score
- **Loan Processing**: Create and manage loans with compound interest calculations
- **Data Ingestion**: Background task processing for importing customer and loan data from Excel files
- **RESTful APIs**: Complete REST API for all operations

## Technology Stack

- **Backend**: Django 5.x with Django REST Framework
- **Database**: PostgreSQL 16
- **Task Queue**: Celery with Redis
- **Containerization**: Docker & Docker Compose
- **Data Processing**: Pandas for Excel/CSV file processing

## Quick Start

### Prerequisites
- Docker and Docker Compose installed
- Git

### Setup and Run

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd credit-approval-system
   ```

2. **Start the application**
   ```bash
   docker-compose up --build
   ```

   This will start:
   - Django web server on `http://localhost:8000`
   - PostgreSQL database on `localhost:5432`
   - Redis server on `localhost:6379`
   - Celery worker for background tasks

3. **Initialize the database**
   ```bash
   # In a new terminal
   docker-compose exec web python manage.py migrate
   ```

4. **Load sample data**
   ```bash
   # Trigger data ingestion
   curl -X POST http://localhost:8000/ingest-data
   ```

## API Endpoints

### 1. Register Customer
**POST** `/register`

Register a new customer with automatic credit limit calculation.

**Request Body:**
```json
{
    "first_name": "John",
    "last_name": "Doe",
    "age": 30,
    "monthly_income": 50000,
    "phone_number": "9876543210"
}
```

**Response:**
```json
{
    "customer_id": 1,
    "name": "John Doe",
    "age": 30,
    "monthly_income": 50000,
    "approved_limit": 1800000,
    "phone_number": "9876543210"
}
```

### 2. Check Loan Eligibility
**POST** `/check-eligibility`

Check if a customer is eligible for a loan with credit score-based interest rate corrections.

**Request Body:**
```json
{
    "customer_id": 1,
    "loan_amount": 500000,
    "interest_rate": 10.5,
    "tenure": 24
}
```

**Response:**
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

### 3. Create Loan
**POST** `/create-loan`

Process and create a new loan based on eligibility.

**Request Body:**
```json
{
    "customer_id": 1,
    "loan_amount": 500000,
    "interest_rate": 10.5,
    "tenure": 24
}
```

**Response:**
```json
{
    "loan_id": 1,
    "customer_id": 1,
    "loan_approved": true,
    "message": "Loan approved",
    "monthly_installment": 23026.69
}
```

### 4. View Loan Details
**GET** `/view-loan/{loan_id}`

Get detailed information about a specific loan.

**Response:**
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

### 5. View Customer Loans
**GET** `/view-loans/{customer_id}`

Get all current loans for a specific customer.

**Response:**
```json
[
    {
        "loan_id": 1,
        "loan_amount": 500000.0,
        "interest_rate": 10.5,
        "monthly_installment": 23026.69,
        "repayments_left": 18
    }
]
```

## Credit Scoring Algorithm

The system uses a comprehensive credit scoring algorithm (0-100 scale) based on:

1. **Payment History (40 points)**: Ratio of EMIs paid on time
2. **Number of Loans (15 points)**: Fewer loans = better score
3. **Current Year Activity (15 points)**: Less activity = better score
4. **Loan Volume vs Limit (30 points)**: Lower utilization = better score

### Interest Rate Slabs

- **Score > 50**: Approve at requested rate
- **30 < Score ≤ 50**: Approve with minimum 12% interest
- **10 < Score ≤ 30**: Approve with minimum 16% interest  
- **Score ≤ 10**: Reject loan

### Additional Rules

- If current loans > approved limit → Credit score = 0
- If total EMIs > 50% of monthly salary → Reject loan

## Data Files

The system expects Excel files in the `/data` directory:

- `customer_data.xlsx`: Customer information
- `loan_data.xlsx`: Historical loan data

Sample files are provided for testing.

## Development

### Project Structure
```
backend/
├── credit_system/          # Django project settings
├── customers/              # Customer management app
├── loans/                  # Loan management app
├── core/                   # Core utilities
├── manage.py
└── requirements.txt

data/                       # Excel data files
docker-compose.yml          # Docker services configuration
.env                        # Environment variables
```

### Running Tests
```bash
docker-compose exec web python manage.py test
```

### Accessing Database
```bash
docker-compose exec db psql -U credituser -d creditdb
```

### Monitoring Celery
```bash
docker-compose logs worker
```

## Environment Variables

Key environment variables (defined in `.env`):

- `DJANGO_SECRET_KEY`: Django secret key
- `DJANGO_DEBUG`: Debug mode (True/False)
- `POSTGRES_DB`: Database name
- `POSTGRES_USER`: Database user
- `POSTGRES_PASSWORD`: Database password
- `REDIS_HOST`: Redis server host

## API Testing

You can test the APIs using curl, Postman, or any HTTP client:

```bash
# Register a customer
curl -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{"first_name":"Test","last_name":"User","age":25,"monthly_income":60000,"phone_number":"1234567890"}'

# Check eligibility
curl -X POST http://localhost:8000/check-eligibility \
  -H "Content-Type: application/json" \
  -d '{"customer_id":1,"loan_amount":100000,"interest_rate":12,"tenure":12}'
```

## Troubleshooting

1. **Database Connection Issues**: Ensure PostgreSQL container is running
2. **Celery Tasks Not Processing**: Check Redis connection and worker logs
3. **Data Ingestion Fails**: Verify Excel files are in `/data` directory with correct format
4. **API Errors**: Check Django logs with `docker-compose logs web`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License.
