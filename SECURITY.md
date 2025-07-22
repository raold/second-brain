# Security Policy

## Supported Versions

We actively support the current stable and development versions. The v2.8.x series represents the current architecture with AI reasoning, knowledge graphs, and advanced content analysis.

| Version | Supported        | Security Level | Notes |
| ------- | ---------------- | -------------- | ----- |
| 2.8.x   | ✅ **Active**     | ⭐⭐⭐⭐⭐ High | Current stable (AI Reasoning + Advanced Analysis) |
| 2.4.x   | ✅ **Maintenance** | ⭐⭐⭐⭐ Good  | Security patches and critical fixes only |
| 2.3.x   | ⚠️ **End of Life** | ⭐⭐ Limited | No updates, upgrade recommended |
| < 2.2   | ❌ **Unsupported** | ⚠️ None    | Legacy versions discontinued |

**Current Stable**: v2.8.1 | **Development**: v2.9.0

We strongly encourage all users to upgrade to v2.8.x for improved security, performance, AI reasoning capabilities, and advanced NLP features.

## Single-User Architecture

**Second Brain v2.x is designed as a personal, single-user AI memory system.** Our security model reflects this use case:

### Security Scope
- ✅ **Personal Data Protection**: Secure storage of individual memories and embeddings
- ✅ **API Authentication**: Simple token-based access control for personal use
- ✅ **Local Deployment**: Designed for self-hosted, single-user environments
- ✅ **Advanced NLP Processing**: Secure handling of content analysis operations
- ❌ **Multi-tenancy**: Not designed for multiple users or shared environments
- ❌ **Enterprise Features**: No RBAC, user management, or complex authorization

### Threat Model
**Primary Concerns:**
- Unauthorized API access to personal data
- Data exposure through misconfigured deployment
- OpenAI API key compromise
- Database credential exposure
- NLP model security (transformer models)
- Graph data privacy

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
- **NLP Model Isolation**: Transformer models run in isolated contexts
- **Graph Data Validation**: Entity and relationship validation before storage

### 🔄 **In Development** (v2.9.0)
- **Enhanced Input Sanitization**: Advanced validation for memory content and metadata
- **Rate Limiting**: Protection against API abuse
- **Security Headers**: HTTP security headers for web dashboard
- **Audit Logging**: Security event logging and monitoring
- **Backup Encryption**: Encrypted backup and restore functionality
- **Model Security**: Sandboxed execution for transformer models
- **Graph Privacy**: Access control for sensitive entity relationships

### ⏳ **Future Considerations**
- **Encryption at Rest**: Database-level encryption for sensitive memories
- **HTTPS Enforcement**: TLS termination for production deployments
- **Advanced Audit Logging**: ML-based anomaly detection
- **Federated Learning**: Privacy-preserving model updates

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
- Isolate NLP model execution environments
```

### **Security Checklist**
- [ ] Strong, unique API tokens (not default values)
- [ ] Secure PostgreSQL installation with updated passwords
- [ ] OpenAI API key secured and regularly rotated
- [ ] `.env` files excluded from version control
- [ ] Database accessible only from application host
- [ ] Regular system updates and dependency management
- [ ] Network firewall rules limiting external access
- [ ] NLP models downloaded from trusted sources only
- [ ] Regular security updates for transformer dependencies

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
- **NLP Processing**: All content analysis happens locally
- **Graph Data**: Entity relationships stored locally only

### **Access Control**
- **Single Token**: One API key for all operations (suitable for personal use)
- **No User Management**: No complex authentication systems
- **Network Security**: Rely on network-level access control
- **API Endpoint Protection**: All new analysis endpoints require authentication

### **Operational Security**
- **Regular Backups**: Implement personal backup strategy for memory data
- **Key Rotation**: Periodically rotate OpenAI API keys and database passwords
- **Update Management**: Keep system dependencies and PostgreSQL updated
- **Monitoring**: Basic logging for unusual API activity
- **Model Updates**: Regular updates for NLP models and dependencies

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
- **Model Execution**: Transformer models run with full system access

## Version-Specific Security Notes

### v2.8.x (Current)
- Enhanced NLP processing requires additional dependencies
- Transformer models may consume significant memory
- Graph visualization runs client-side (secure)
- All analysis happens locally, no external API calls

### v2.4.x (Maintenance)
- Stable PostgreSQL + pgvector architecture
- Well-tested security model
- Limited to core functionality
- Recommended for conservative deployments

## Resources

- [Project Documentation](../README.md)
- [Architecture Overview](../docs/ARCHITECTURE.md)
- [Testing Guide](../docs/TESTING.md)
- [Deployment Guide](../docs/DEPLOYMENT.md)
- [Version History](../CHANGELOG.md)
- [Release Notes v2.8.1](../RELEASE_NOTES_v2.8.1.md)

---

**Last Updated**: January 22, 2025  
**Security Model**: Single-User Personal AI System  
**Current Stable**: v2.8.1 | **Development**: v2.9.0  
**Next Security Review**: v2.9.0 (Collaboration Features)