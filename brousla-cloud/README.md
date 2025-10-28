# Brousla Cloud - Subscription & Entitlement Service

FastAPI-based cloud service for managing subscriptions, entitlements, and licensing for Brousla app.

## Quick Start

```bash
# 1. Generate RSA keys
python3 scripts/generate_keys.py

# 2. Setup environment
cp .env.example .env
# Paste keys and Stripe credentials into .env

# 3. Start services
docker-compose up -d

# 4. Run tests
pytest

# 5. Verify
curl http://localhost:8000/health
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Database Migrations

```bash
# Create migration
alembic revision --autogenerate -m "description"

# Run migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Running Tests

```bash
# All tests
pytest

# Specific test file
pytest tests/test_auth.py

# With coverage
pytest --cov=app tests/

# Verbose
pytest -v
```

## Monitoring

```bash
# View logs
docker-compose logs -f api

# Database logs
docker-compose logs -f db

# Check running containers
docker-compose ps
```

## Production Deployment

1. Use a production-grade WSGI server (Gunicorn)
2. Enable HTTPS/TLS
3. Use managed PostgreSQL (RDS, Cloud SQL, etc.)
4. Store secrets in environment/secrets manager
5. Enable monitoring and logging
6. Configure backup strategy
7. Set up CI/CD pipeline

## Environment Variables

See `.env.example` for all required variables.

## License

ISC
