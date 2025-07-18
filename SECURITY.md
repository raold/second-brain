# Security Policy

## Supported Versions

We actively support the current stable and development versions. The v2.4.x series represents the current architecture with enhanced security and simplified deployment.

| Version | Supported        | Security Level | Notes |
| ------- | ---------------- | -------------- | ----- |
| 2.4.x   | ✅ **Active**     | ⭐⭐⭐⭐⭐ High | Current development (PostgreSQL + pgvector) |
| 2.3.x   | ✅ **Maintenance** | ⭐⭐⭐⭐ Good  | Previous stable release |
| 2.2.x   | ⚠️ **End of Life** | ⭐⭐⭐ Basic | Security patches only |
| < 2.2   | ❌ **Unsupported** | ⭐ Minimal    | Legacy versions discontinued |

**Current Stable**: v2.4.1 | **Development**: v2.4.2

We strongly encourage all users to upgrade to v2.4.x for improved security, performance, and the latest features.

## Single-User Architecture

**Second Brain v2.x is designed as a personal, single-user AI memory system.** Our security model reflects this use case:

### Security Scope
- ✅ **Personal Data Protection**: Secure storage of individual memories and embeddings
- ✅ **API Authentication**: Simple token-based access control for personal use
- ✅ **Local Deployment**: Designed for self-hosted, single-user environments
- ❌ **Multi-tenancy**: Not designed for multiple users or shared environments
- ❌ **Enterprise Features**: No RBAC, user management, or complex authorization

### Threat Model
**Primary Concerns:**
- Unauthorized API access to personal data
- Data exposure through misconfigured deployment
- OpenAI API key compromise
- Database credential exposure

**Out of Scope:**
- Multi-user access control
- Privilege escalation between users
- Enterprise compliance (SOC2, GDPR, etc.)
- Distributed system security

## Current Security Features

### ✅ **Implemented Protections**
- **API Key Authentication**: Simple token-based access control
- **Environment Variable Security**: Secrets stored in `.env` files (not committed)
- **PostgreSQL Security**: Database credentials and connection security
- **OpenAI API Protection**: Secure API key handling for embeddings
- **Input Validation**: Pydantic models for request validation
- **Mock Database Mode**: Testing without external API dependencies

### 🔄 **In Development** (v2.5.0)
- **Enhanced Input Sanitization**: Advanced validation for memory content and metadata
- **Rate Limiting**: Protection against API abuse
- **Security Headers**: HTTP security headers for web dashboard
- **Audit Logging**: Security event logging and monitoring
- **Backup Encryption**: Encrypted backup and restore functionality
- **Rate Limiting**: API endpoint protection against abuse
- **Security Headers**: Basic HTTP security headers
- **Error Handling**: Secure error responses without information leakage

### ⏳ **Future Considerations**
- **Encryption at Rest**: Database-level encryption for sensitive memories
- **HTTPS Enforcement**: TLS termination for production deployments
- **Audit Logging**: Security event logging for monitoring
- **Backup Security**: Encrypted backup strategies

## Deployment Security

### **Recommended Single-User Setup**
```bash
# Local development (default)
export API_TOKENS="your-personal-token"
export OPENAI_API_KEY="your-openai-key" 
export DATABASE_URL="postgresql://user:pass@localhost:5432/second_brain"

# Self-hosted production
- Use strong, unique API tokens
- Secure PostgreSQL with network restrictions
- Deploy behind reverse proxy with HTTPS
- Regular database backups with encryption
```

### **Security Checklist**
- [ ] Strong, unique API tokens (not default values)
- [ ] Secure PostgreSQL installation with updated passwords
- [ ] OpenAI API key secured and regularly rotated
- [ ] `.env` files excluded from version control
- [ ] Database accessible only from application host
- [ ] Regular system updates and dependency management
- [ ] Network firewall rules limiting external access

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly:

📧 **security@oldham.io**

### Include the Following Information:
- **Description**: Clear explanation of the vulnerability
- **Impact**: Potential security implications for single-user deployments
- **Reproduction**: Step-by-step instructions to reproduce
- **Environment**: Version, OS, deployment method, configuration
- **Proof of Concept**: Safe demonstration (if applicable)

### Response Timeline:
- **Initial Response**: Within **3 business days**
- **Severity Assessment**: Within **5 business days**
- **Resolution Target**: 
  - Critical: 7 days
  - High: 14 days
  - Medium: 30 days
  - Low: Next minor release

## Security Considerations for Personal Use

### **Data Privacy**
- **Local Control**: All memory data stored in your own PostgreSQL database
- **API Interactions**: Only with OpenAI for embeddings (can be disabled with mock mode)
- **No Telemetry**: No usage data collected or transmitted
- **Export Capability**: Full data export and portability

### **Access Control**
- **Single Token**: One API key for all operations (suitable for personal use)
- **No User Management**: No complex authentication systems
- **Network Security**: Rely on network-level access control

### **Operational Security**
- **Regular Backups**: Implement personal backup strategy for memory data
- **Key Rotation**: Periodically rotate OpenAI API keys and database passwords
- **Update Management**: Keep system dependencies and PostgreSQL updated
- **Monitoring**: Basic logging for unusual API activity

## Known Limitations

### **Security Trade-offs for Simplicity**
- **No Password Policies**: Simple token-based authentication
- **No Session Management**: Stateless API design
- **No Audit Trail**: Minimal logging for personal use
- **No Data Loss Prevention**: Basic input validation only

### **Acceptable Risks for Single-User Context**
- **Shared Secret**: Single API token acceptable for personal use
- **No Rate Limiting** (currently): Less critical for single-user scenarios
- **Basic Error Handling**: Detailed errors acceptable for personal debugging

## Resources

- [Project Documentation](../README.md)
- [Architecture Overview](../docs/ARCHITECTURE.md)
- [Testing Guide](../docs/TESTING.md)
- [Deployment Guide](../docs/DEPLOYMENT.md)
- [Version History](../CHANGELOG.md)

---

**Last Updated**: July 17, 2025  
**Security Model**: Single-User Personal AI System  
**Current Stable**: v2.4.1 | **Development**: v2.4.2  
**Next Security Review**: v2.4.0 (Security Enhancement)
