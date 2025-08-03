# Credit Approval System (Django + DRF + Celery + Postgres + Redis)

A dockerized backend that registers customers, evaluates loan eligibility, creates loans, and ingests historical data from Excel using background workers.

## Tech Stack
- **Django 5 + DRF**
- **PostgreSQL 16**
- **Redis 7 + Celery**
- **Docker Compose**
- **pandas + openpyxl** (Excel ingestion)

## Project Structure
credit_approval_system/
├─ backend/
│ ├─ credit_system/ # Django project (settings, urls, celery init)
│ ├─ customers/ # Register + ingestion endpoint
│ ├─ loans/ # Eligibility, create-loan, view-loan(s)
│ ├─ requirements.txt
│ └─ Dockerfile
├─ data/ # Mount for Excel files (not committed)
├─ .env # Local env (ignored)
├─ .env.example # Sample env for reviewers
├─ .gitignore
└─ docker-compose.yml

## Getting Started

### Prerequisites
- Docker & Docker Compose installed
- Make sure ports `8000`, `5432`, and `6379` are free

### Setup
```bash
# Clone the repository
git clone <your_repo_url>
cd credit_approval_system

# Copy environment example and edit if needed
cp .env.example .env

# Start services with build
docker compose up -d --build

# Apply migrations
docker compose exec web python manage.py migrate

# Start all services
docker compose up -d

# Stop all services
docker compose down

## API Endpoints

### 1) Register Customer — `POST /register`
**Request**
```json
{
  "first_name": "Amit",
  "last_name": "Kumar",
  "age": 28,
  "monthly_income": 60000,
  "phone_number": "9876543210"
}

#Response (example)

{
  "customer_id": 1,
  "name": "Amit Kumar",
  "age": 28,
  "monthly_income": 60000,
  "approved_limit": 2200000,
  "phone_number": "9876543210"
}

#Check Eligibility

{
  "customer_id": 1,
  "loan_amount": 250000,
  "interest_rate": 12.0,
  "tenure": 24
}

#response(example)

{
  "customer_id": 1,
  "approval": true,
  "interest_rate": 12.0,
  "corrected_interest_rate": 12.0,
  "tenure": 24,
  "monthly_installment": 11768.37
}

#Create Loan 

{
  "customer_id": 1,
  "loan_amount": 250000,
  "interest_rate": 12.0,
  "tenure": 24
}

#response(example)

{
  "loan_id": 1,
  "customer_id": 1,
  "loan_approved": true,
  "message": "Loan approved",
  "monthly_installment": 11768.37
}

#View Loan

{
  "loan_id": 1,
  "customer": {
    "id": 1,
    "first_name": "Amit",
    "last_name": "Kumar",
    "phone_number": "9876543210",
    "age": 28
  },
  "loan_amount": 250000.0,
  "interest_rate": 12.0,
  "monthly_installment": 11768.37,
  "tenure": 24
}

# View Loans by Customer 

[
  {
    "loan_id": 1,
    "loan_amount": 250000.0,
    "interest_rate": 12.0,
    "monthly_installment": 11768.37,
    "repayments_left": 24
  }
]


## Data Ingestion

### Endpoint — `POST /ingest-data`
Uses a background worker (Celery) to read `/data/customer_data.xlsx` and `/data/loan_data.xlsx` files and insert/update records in the database.

> **Note:** The `./data` folder in your project is mounted to `/data` in the container via docker-compose.  
> Place the Excel files in the local `data/` folder before running ingestion.

### Steps

```bash
# 1) Place the Excel files
# Put these in the local ./data folder
# - customer_data.xlsx
# - loan_data.xlsx

# 2) Start services
docker compose up -d

# 3) Trigger ingestion
curl -X POST http://localhost:8000/ingest-data

# 4) Watch worker logs to monitor progress
docker compose logs -f worker

# Trigger ingestion
curl.exe -X POST http://localhost:8000/ingest-data

# Watch logs
docker compose logs -f worker

## Tests

### Run
```bash
docker compose exec web python manage.py test -v 2

