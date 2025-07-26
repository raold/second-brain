# OpenAI API Key Setup Guide

## GitHub Actions Setup (Required for CI/CD)

### 1. Add Secret to GitHub Repository

1. Go to your repository on GitHub: `https://github.com/raold/second-brain`
2. Click on **Settings** (in the repository, not your profile)
3. In the left sidebar, click **Secrets and variables** > **Actions**
4. Click **New repository secret**
5. Add the following:
   - **Name**: `OPENAI_API_KEY`
   - **Value**: Your OpenAI API key (should start with `sk-`)
6. Click **Add secret**

### 2. Verify the Setup

I've created a test workflow to verify your API key is working. After pushing this commit:

1. Go to the **Actions** tab in your GitHub repository
2. You should see two workflows:
   - **CI Tests** - Regular test suite
   - **Test OpenAI API Key** - Specific test for the API key

3. The "Test OpenAI API Key" workflow will:
   - Check if the key is set
   - Verify the format (starts with `sk-`)
   - Test actual API connection
   - List available models

### 3. Manual Workflow Run

You can also manually trigger the test:

1. Go to Actions tab
2. Click on "Test OpenAI API Key" workflow
3. Click "Run workflow" button
4. Select branch and click "Run workflow"

## Local Development Setup

### Windows
```cmd
set OPENAI_API_KEY=your-api-key-here
python scripts/test_openai_key.py
```

### Linux/Mac
```bash
export OPENAI_API_KEY=your-api-key-here
python scripts/test_openai_key.py
```

### Permanent Setup (Optional)

#### Windows
Add to your user environment variables:
1. Win + X > System > Advanced system settings
2. Environment Variables > User variables > New
3. Variable name: `OPENAI_API_KEY`
4. Variable value: Your API key

#### Linux/Mac
Add to your `~/.bashrc` or `~/.zshrc`:
```bash
export OPENAI_API_KEY="your-api-key-here"
```

## Troubleshooting

### If CI Tests Are Failing
1. Check if OPENAI_API_KEY is in GitHub secrets (not variables)
2. Ensure the key starts with `sk-`
3. Check the key hasn't expired or been revoked
4. Look at the "Test OpenAI API Key" workflow output for details

### Getting an API Key
1. Go to https://platform.openai.com/api-keys
2. Create a new secret key
3. Copy it immediately (you won't see it again)
4. Add it to GitHub secrets as described above

## Security Notes
- Never commit your API key to the repository
- Use GitHub secrets for CI/CD
- Use environment variables for local development
- The test scripts will only show the first few characters of the key