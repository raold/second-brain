# Secrets Management Guide

**Single-User AI Memory System** | Security-first approach | Zero secrets in repository

---

## Critical Security Rule

**⚠️ NEVER COMMIT SECRETS TO REPOSITORY ⚠️**

All sensitive data → GitHub Secrets + Environment Variables only

---

## Secret Storage Matrix

| Environment | Storage Method | Access Pattern | Security Level |
|-------------|----------------|----------------|----------------|
| **Local Development** | `.env` file (gitignored) | `os.getenv()` | Medium |
| **GitHub Actions** | Repository Secrets | `${{ secrets.NAME }}` | High |
| **Production** | Encrypted vault/secrets manager | Environment injection | Maximum |
| **Testing** | Mock objects only | No real secrets | N/A |

---

## Local Development Setup

**Step 1: Create `.env` file** (NEVER commit this)
```bash
# .env - Add to .gitignore immediately
OPENAI_API_KEY=sk-your_actual_key_here
DATABASE_URL=postgresql://user:pass@localhost:5432/second_brain  
AUTH_TOKEN=your_32_char_minimum_token_here
```

**Step 2: Verify `.gitignore` protection**
```gitignore
# Environment variables - CRITICAL
.env
.env.*
*.env
```

**Step 3: Load in application**
```python
import os
from dotenv import load_dotenv

load_dotenv()  # Loads .env file
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY not configured")
```

---

## GitHub Actions Integration

**Repository Secrets Configuration**
1. GitHub Repository → Settings → Secrets and variables → Actions
2. New repository secret for each sensitive value:

| Secret Name | Purpose | Format | Notes |
|-------------|---------|--------|--------|
| `OPENAI_API_KEY` | OpenAI API access | `sk-...` | Required for embeddings |
| `AUTH_TOKEN` | API authentication | 32+ chars | Strong entropy required |
| `DATABASE_URL` | Production DB | `postgresql://...` | Connection string |

**Workflow Implementation**
```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy with Secrets
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          AUTH_TOKEN: ${{ secrets.AUTH_TOKEN }}
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
        run: |
          python -m app.main
```

---

## Testing Strategy Matrix

| Test Type | Secret Usage | Implementation | API Costs |
|-----------|--------------|----------------|-----------|
| **Unit Tests** | ❌ None | Mock all external services | $0 |
| **Integration** | ❌ None | Mock OpenAI + Test DB | $0 |
| **End-to-End** | ⚠️ Test keys only | Separate test environment | Minimal |
| **Manual** | ✅ Dev keys | Local `.env` file | Development |

**Mock Implementation Example**
```python
# tests/fixtures/external_services.py
@patch('openai.Client')
def test_memory_storage(mock_openai):
    mock_openai.embeddings.create.return_value.data[0].embedding = [0.1] * 1536
    # Test proceeds with mocked response
```

---

## Security Validation Checklist

| Category | Requirement | Status | Validation Command |
|----------|-------------|--------|---------------------|
| **Code** | No hardcoded secrets | ⬜ | `grep -r "sk-" --exclude-dir=.git .` |
| | No secrets in logs | ⬜ | Review logging statements |
| | Environment validation | ⬜ | Required vars check on startup |
| **Repository** | `.env` in `.gitignore` | ⬜ | `git check-ignore .env` |
| | No secrets in history | ⬜ | `git log --all -p | grep "sk-"` |
| **GitHub** | All secrets configured | ⬜ | Settings → Secrets list |
| | Workflow references correct names | ⬜ | `.github/workflows/*.yml` review |

---

## Common Vulnerabilities & Prevention

| Vulnerability | Risk Level | Prevention | Detection |
|---------------|------------|------------|-----------|
| **Hardcoded API keys** | 🔴 Critical | Environment variables only | Code scanning |
| **Secrets in logs** | 🟡 High | Sanitize log output | Log analysis |
| **Committed .env files** | 🔴 Critical | Gitignore + pre-commit hooks | History scanning |
| **Weak auth tokens** | 🟡 High | Minimum 32 chars, high entropy | Token strength validation |
| **Production keys in dev** | 🟡 High | Separate key sets | Environment tracking |

---

## Error Resolution Decision Tree

**Missing Secret Error**: `KeyError: 'OPENAI_API_KEY'`
```
Environment check:
├─ Local dev? → Verify .env file exists and contains key
├─ GitHub Actions? → Check repository secrets configuration
├─ Production? → Verify environment variable injection
└─ Testing? → Should use mocks, not real secrets
```

**Secret Not Loading**
```
Check sequence:
1. Spelling: Exact case match (OPENAI_API_KEY vs openai_api_key)
2. Scope: Secret available in current environment/workflow
3. Syntax: Proper ${{ secrets.NAME }} format in workflows
4. Loading: dotenv.load() called before os.getenv()
```

---

## Implementation Examples

**Environment Validation (Startup)**
```python
def validate_secrets():
    required = ["OPENAI_API_KEY", "DATABASE_URL", "AUTH_TOKEN"]
    missing = [var for var in required if not os.getenv(var)]
    if missing:
        raise EnvironmentError(f"Missing required secrets: {', '.join(missing)}")

# Call on application startup
validate_secrets()
```

**Secure Logging Pattern**
```python
import logging

def safe_log_config():
    # Mask sensitive values in logs
    sensitive_keys = ["OPENAI_API_KEY", "AUTH_TOKEN", "DATABASE_URL"]
    config = {k: "***MASKED***" if k in sensitive_keys else v 
              for k, v in os.environ.items()}
    logging.info(f"Configuration loaded: {config}")
```

**Production Secret Rotation**
```python
# Rotate secrets without downtime
def rotate_api_key():
    old_key = os.getenv("OPENAI_API_KEY")
    new_key = os.getenv("OPENAI_API_KEY_NEW")
    
    if new_key and validate_api_key(new_key):
        # Switch to new key
        os.environ["OPENAI_API_KEY"] = new_key
        logging.info("API key rotated successfully")
        return True
    return False
```

---

## Security Metrics & Monitoring

| Metric | Target | Current | Trend |
|--------|--------|---------|-------|
| **Secrets in code** | 0 | 0 | ✅ Stable |
| **Failed auth attempts** | <1% | Monitor | 📊 Tracking |
| **Secret age (days)** | <90 | Varies | ⏰ Rotation needed |
| **Environment leaks** | 0 | 0 | ✅ Clean |

**Automated Scanning**
- GitHub secret scanning: Enabled
- Pre-commit hooks: Recommended  
- Regular audits: Monthly
- Rotation schedule: Quarterly

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