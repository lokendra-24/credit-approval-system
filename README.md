Credit Approval System
A minimal backend service to register customers, check credit eligibility, and create/view loans. Built with Django + DRF, backed by PostgreSQL, background tasks via Celery + Redis, and containerized with Docker Compose.

Features
Customer registration & profile

Credit eligibility check (async task-ready)

Loan creation & listing

RESTful APIs with DRF

Dockerized dev setup

Tech Stack
Django · Django REST Framework · PostgreSQL · Redis · Celery · Docker & Compose · PyTest/Unittest

#quick start(with docker)
# 1) Copy env template and fill values
cp .env.example .env

# 2) Build & start all services
docker-compose up --build -d

# 3) Run migrations & create superuser
docker-compose exec backend python manage.py migrate
docker-compose exec backend python manage.py createsuperuser
