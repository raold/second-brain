# Secrets Management

## Environment Variables
Never commit `.env` files. Use `.env.example` as template.

## Required Secrets
```bash
# .env
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql://user:pass@localhost/db
SECRET_KEY=generate-random-string
```

## Security Checks
```bash
# Before committing
python scripts/check_secrets.py
```

## Best Practices
1. Rotate keys regularly
2. Use different keys per environment
3. Never log sensitive values
4. Store production secrets in vault (HashiCorp, AWS Secrets Manager)

## If Keys Exposed
1. Rotate immediately at provider
2. Check git history for exposure
3. Consider repo rotation if public