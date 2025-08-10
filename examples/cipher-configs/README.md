# Cipher Configuration Examples

This directory contains example configurations for different use cases of Second Brain with optional Cipher integration.

## Configuration Files

### 1. `solo-developer.env`
- **Use Case**: Individual developers using Second Brain standalone
- **Cipher**: Disabled
- **Best For**: Personal knowledge management without IDE integration

### 2. `ai-ide-user.env`
- **Use Case**: Developers using AI-powered IDEs (Cursor, Windsurf, Claude Desktop)
- **Cipher**: Enabled with local server
- **Best For**: Getting memories directly in your AI coding assistant

### 3. `team-development.env`
- **Use Case**: Development teams sharing knowledge
- **Cipher**: Enabled with hosted Byterover service
- **Best For**: Team collaboration and knowledge sharing across IDEs

## Quick Start

1. Choose the configuration that matches your use case
2. Copy it to your project root as `.env`:
   ```bash
   cp examples/cipher-configs/solo-developer.env .env
   ```
3. Update the values with your actual API keys and settings
4. Start Second Brain:
   ```bash
   docker-compose up -d
   ```

## Configuration Decision Tree

```
Do you work alone or in a team?
├─ Alone
│  └─ Do you use AI-powered IDEs?
│     ├─ No → Use `solo-developer.env`
│     └─ Yes → Use `ai-ide-user.env`
└─ Team
   └─ Use `team-development.env`
```

## Migrating Between Configurations

### From Solo to AI-IDE
1. Set `CIPHER_ENABLED=true`
2. Install Cipher locally
3. Configure your IDE's MCP settings

### From AI-IDE to Team
1. Get team workspace credentials from Byterover
2. Update `CIPHER_URL` to hosted service
3. Add `CIPHER_API_KEY` and `CIPHER_WORKSPACE_ID`
4. Adjust security settings for production

## Security Notes

- Never commit `.env` files with real API keys
- Use strong passwords in production
- Rotate API keys regularly
- Use environment-specific secrets management

## Additional Resources

- [Cipher Integration Guide](../../docs/CIPHER_INTEGRATION_GUIDE.md)
- [Second Brain Documentation](../../docs/DOCUMENTATION_INDEX.md)
- [Cipher GitHub Repository](https://github.com/campfirein/cipher)