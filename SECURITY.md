# 🔒 Second Brain Security Guide

## ⚠️ CRITICAL SECURITY NOTICE

**NEVER commit API keys, passwords, or secrets to Git!**

This project has security measures in place to prevent accidental exposure of sensitive information.

## 🚨 Immediate Actions for New Developers

1. **Copy the template file for local development:**
   ```bash
   cp .env.local.template .env.local
   ```

2. **Add your actual API keys to `.env.local`** (this file is gitignored)

3. **Run security check before commits:**
   ```bash
   python scripts/check_secrets.py
   ```

## 📋 Security Checklist

### Environment Files
- ✅ **Use `.env.local`** for local development (automatically ignored by git)
- ✅ **Never commit** `.env`, `.env.local`, `.env.production` files
- ✅ **Use `.env.example`** to show required variables without values
- ✅ **Run security checks** before every commit

### API Keys
- ✅ **Store in environment variables** - never hardcode in source files
- ✅ **Use placeholder values** in example files
- ✅ **Rotate keys regularly** (monthly recommended)
- ✅ **Monitor API usage** for unusual activity

### Git Security
- ✅ **Check git status** before committing
- ✅ **Review changes** carefully for accidental secrets
- ✅ **Use pre-commit hooks** to catch secrets automatically
- ✅ **Clean git history** if secrets are accidentally committed

## 🔑 Managing Secrets

### Local Development

1. **Create your local environment file:**
   ```bash
   cp .env.local.template .env.local
   ```

2. **Add your API keys:**
   ```bash
   # Edit .env.local and add your keys:
   OPENAI_API_KEY=sk-proj-your_actual_key_here
   ANTHROPIC_API_KEY=sk-ant-your_actual_key_here
   ```

3. **Verify it's not tracked:**
   ```bash
   git status  # .env.local should NOT appear
   ```

### Production Deployment

Use secure secret management services:
- **AWS**: AWS Secrets Manager or Parameter Store
- **Azure**: Azure Key Vault
- **GCP**: Google Secret Manager
- **Heroku**: Config Vars
- **Docker**: Docker Secrets

Example with AWS Secrets Manager:
```python
import boto3
import json

def get_secret(secret_name):
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response['SecretString'])

# In your app
secrets = get_secret('second-brain/production')
OPENAI_API_KEY = secrets['openai_api_key']
```

## 🛡️ Security Tools

### 1. Secret Detection Script

Run before every commit:
```bash
python scripts/check_secrets.py
```

This script checks for:
- Exposed API keys in code
- Tracked .env files in git
- Weak passwords
- Missing security configurations

### 2. Pre-commit Hook (Recommended)

Install pre-commit hooks:
```bash
pip install pre-commit
pre-commit install
```

Create `.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
```

### 3. Git History Cleaning

If you accidentally commit secrets:

**Option 1: BFG Repo-Cleaner (Easiest)**
```bash
# Download BFG
wget https://repo1.maven.org/maven2/com/madgag/bfg/1.14.0/bfg-1.14.0.jar

# Create a backup
git clone --mirror https://github.com/yourusername/second-brain.git second-brain-backup

# Remove secrets
java -jar bfg-1.14.0.jar --replace-text passwords.txt second-brain-backup

# Push cleaned history
cd second-brain-backup
git reflog expire --expire=now --all && git gc --prune=now --aggressive
git push
```

**Option 2: git filter-branch**
```bash
git filter-branch --force --index-filter \
  'git rm --cached --ignore-unmatch .env*' \
  --prune-empty --tag-name-filter cat -- --all
```

## 🔍 Security Monitoring

### API Key Monitoring

1. **OpenAI Dashboard**: Monitor usage at https://platform.openai.com/usage
2. **Anthropic Console**: Check usage at https://console.anthropic.com/
3. **Set up alerts** for unusual usage patterns

### GitHub Security

1. **Enable GitHub Secret Scanning** in repository settings
2. **Review security alerts** regularly
3. **Use branch protection** for main branch
4. **Require PR reviews** before merging

## 🚫 What NOT to Do

❌ **Never commit these files:**
- `.env`, `.env.local`, `.env.production`
- Any file with real API keys
- Private keys (`.pem`, `.key`, `.cert`)
- Database dumps with sensitive data

❌ **Never hardcode in source:**
```python
# WRONG - Never do this!
OPENAI_API_KEY = "sk-proj-abc123..."

# RIGHT - Use environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
```

❌ **Never log sensitive data:**
```python
# WRONG
logger.info(f"Using API key: {api_key}")

# RIGHT
logger.info("API key configured")
```

## 📊 Security Audit Results

Run regular security audits:
```bash
# Check for secrets
python scripts/check_secrets.py

# Check dependencies for vulnerabilities
pip-audit

# Scan Docker images
docker scan second-brain:latest
```

## 🆘 If You Exposed Secrets

**Immediate actions:**

1. **Rotate the exposed keys immediately**
   - OpenAI: https://platform.openai.com/api-keys
   - Anthropic: https://console.anthropic.com/

2. **Remove from git history** (see Git History Cleaning above)

3. **Notify the team** if working in a team environment

4. **Monitor for unauthorized usage**

5. **Update all deployments** with new keys

## 📚 Additional Resources

- [GitHub Secret Scanning](https://docs.github.com/en/code-security/secret-scanning)
- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- [12 Factor App - Config](https://12factor.net/config)
- [git-secrets by AWS](https://github.com/awslabs/git-secrets)

## 🤝 Security Contact

If you discover a security vulnerability, please:
1. **Do NOT** create a public GitHub issue
2. Email security concerns to: [your-email@example.com]
3. Include steps to reproduce if applicable

---

**Remember**: Security is everyone's responsibility. When in doubt, ask for help before committing!

Last Updated: 2025-08-02