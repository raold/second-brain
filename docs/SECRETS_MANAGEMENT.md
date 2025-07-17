# Secrets Management Guide

This guide explains how to properly handle sensitive information like API keys in the Second Brain project.

## Overview

**Never commit secrets to the repository!** All sensitive information should be stored as GitHub Secrets and accessed through environment variables.

## Local Development

### 1. Create a `.env` file

For local development, create a `.env` file in the project root:

```bash
# .env (DO NOT COMMIT THIS FILE)
OPENAI_API_KEY=your_actual_api_key_here
QDRANT_API_KEY=your_qdrant_key_if_needed
POSTGRES_PASSWORD=your_postgres_password
```

### 2. Add `.env` to `.gitignore`

Ensure `.env` is in your `.gitignore` file:

```gitignore
# Environment variables
.env
.env.local
.env.*.local
```

### 3. Load environment variables

The application loads these automatically using `python-dotenv` or similar.

## GitHub Actions

### 1. Add Secrets to GitHub

1. Go to your repository on GitHub
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add each secret with its name and value:
   - `OPENAI_API_KEY`
   - `POSTGRES_PASSWORD`
   - `QDRANT_API_KEY` (if using cloud Qdrant)
   - Any other sensitive values

### 2. Reference Secrets in Workflows

In your workflow files (`.github/workflows/*.yml`), reference secrets like this:

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Run Tests
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          POSTGRES_PASSWORD: ${{ secrets.POSTGRES_PASSWORD }}
        run: |
          pytest tests/
```

### 3. Current Implementation

The project correctly uses secrets in:

- **Deploy Workflow** (`deploy.yml`):
  ```yaml
  env:
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
  ```

- **CI Workflow** (`ci.yaml`):
  - Tests use mocked services, so no API keys needed
  - This is the correct approach for CI testing

## Best Practices

### ✅ DO:

1. **Use Environment Variables**
   ```python
   import os
   api_key = os.getenv("OPENAI_API_KEY")
   if not api_key:
       raise ValueError("OPENAI_API_KEY not set")
   ```

2. **Mock External Services in Tests**
   ```python
   # Tests should use mocks, not real API keys
   @patch('openai.Client')
   def test_something(mock_client):
       # Test with mocked client
   ```

3. **Validate Secrets Exist**
   ```python
   required_secrets = ["OPENAI_API_KEY", "POSTGRES_PASSWORD"]
   missing = [s for s in required_secrets if not os.getenv(s)]
   if missing:
       raise ValueError(f"Missing required secrets: {missing}")
   ```

### ❌ DON'T:

1. **Never Hardcode Secrets**
   ```python
   # NEVER DO THIS
   api_key = "sk-abc123..."  # WRONG!
   ```

2. **Never Print Secrets**
   ```python
   # NEVER DO THIS
   print(f"Using API key: {api_key}")  # WRONG!
   ```

3. **Never Commit .env Files**
   ```bash
   # NEVER DO THIS
   git add .env  # WRONG!
   ```

## Testing Strategy

### Unit Tests
- Use the comprehensive mocking system in `tests/fixtures/external_services.py`
- No real API keys needed
- Tests run fast and don't consume API quotas

### Integration Tests
- Only run in secure environments
- Use separate test API keys if needed
- Never use production keys for testing

## Troubleshooting

### Missing Secret Error
If you see errors like:
```
KeyError: 'OPENAI_API_KEY'
```

1. **Locally**: Check your `.env` file exists and contains the key
2. **CI/CD**: Check the secret is added in GitHub Settings

### Secret Not Loading
If secrets aren't loading:

1. **Check spelling**: Secret names are case-sensitive
2. **Check scope**: Secrets might be scoped to specific environments
3. **Check workflow syntax**: Ensure proper `${{ secrets.NAME }}` format

## Security Checklist

- [ ] All API keys stored as GitHub Secrets
- [ ] `.env` file in `.gitignore`
- [ ] No hardcoded secrets in code
- [ ] No secrets in logs or error messages
- [ ] Tests use mocks, not real services
- [ ] Production uses different keys than development
- [ ] Regular key rotation schedule in place

## Example: Adding a New Secret

1. **Add to GitHub Secrets**:
   - Go to Settings → Secrets → New repository secret
   - Name: `NEW_API_KEY`
   - Value: `your-actual-key`

2. **Update Workflow**:
   ```yaml
   - name: Deploy
     env:
       NEW_API_KEY: ${{ secrets.NEW_API_KEY }}
     run: |
       python deploy.py
   ```

3. **Update Local .env**:
   ```bash
   echo "NEW_API_KEY=your-local-key" >> .env
   ```

4. **Update Code**:
   ```python
   new_key = os.getenv("NEW_API_KEY")
   if not new_key and not testing:
       raise ValueError("NEW_API_KEY required")
   ```

Remember: **Security is everyone's responsibility!** 