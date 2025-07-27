# Security Policy

## Supported Versions

We actively support the current v3.x series with its enterprise-ready architecture. The v3.0.0 release represents a complete architectural transformation with Clean Architecture, event sourcing, and production-grade infrastructure.

| Version | Supported        | Security Level | Notes |
| ------- | ---------------- | -------------- | ----- |
| 3.x     | ✅ **Active**     | ⭐⭐⭐⭐⭐ Maximum | Current stable (Clean Architecture + Enterprise Features) |
| 2.8.x   | 🔧 **Maintenance** | ⭐⭐⭐⭐ Good  | Security patches and critical fixes only |
| 2.4.x   | ⚠️ **End of Life** | ⭐⭐ Limited | No updates, upgrade to v3.x strongly recommended |
| < 2.3   | ❌ **Unsupported** | ⚠️ None    | Legacy versions discontinued |

**Current Stable**: v3.0.0 | **Previous Stable**: v2.8.2

We strongly encourage all users to upgrade to v3.x for enterprise-grade security, scalability, observability, and the complete benefits of Clean Architecture.

## Enterprise-Ready Architecture (v3.x)

**Second Brain v3.x has evolved into an enterprise-ready AI memory system** with production-grade security features. While maintaining simplicity for single-user deployments, v3.x now provides the foundation for secure multi-user and enterprise scenarios:

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

## Current Security Features (v3.0.0)

### ✅ **Implemented Protections**
- **JWT Authentication**: Industry-standard JSON Web Tokens for API security
- **Environment Variable Security**: Secrets management with `.env` files (gitignored)
- **PostgreSQL Security**: Connection pooling, SSL support, and credential isolation
- **OpenAI API Protection**: Secure key handling with automatic rotation support
- **Input Validation**: Pydantic V2 models with strict type checking and validation
- **Dependency Injection**: No hardcoded dependencies, secure service instantiation
- **Event Sourcing**: Complete audit trail of all state changes
- **Structured Logging**: JSON logs with security context and correlation IDs
- **Docker Isolation**: Container-based security boundaries
- **CORS Configuration**: Proper cross-origin resource sharing controls
- **Error Handling**: Sanitized error messages prevent information disclosure
- **Async Architecture**: Protection against blocking attacks

### 🔄 **Security Enhancements in v3.x**
- **Rate Limiting**: Built-in protection against API abuse
- **Security Headers**: Comprehensive HTTP security headers (CSP, HSTS, etc.)
- **Audit Logging**: Full event stream with security event tracking
- **Service Isolation**: Clean Architecture ensures security boundaries
- **Health Checks**: Secure health endpoints that don't expose sensitive data
- **Observability**: OpenTelemetry tracing for security monitoring
- **Database Migrations**: Version-controlled schema changes with Alembic

### ⏳ **Future Considerations**
- **Encryption at Rest**: Database-level encryption for sensitive memories
- **HTTPS Enforcement**: TLS termination for production deployments
- **Advanced Audit Logging**: ML-based anomaly detection
- **Federated Learning**: Privacy-preserving model updates

## Deployment Security

### **Recommended Production Setup (v3.0.0)**
```bash
# Docker-based deployment (recommended)
docker-compose up -d

# Environment configuration (.env)
JWT_SECRET="strong-256-bit-secret"
OPENAI_API_KEY="sk-your-openai-key" 
DATABASE_URL="postgresql://user:pass@postgres:5432/secondbrain"
REDIS_URL="redis://redis:6379"

# Production best practices
- Use Docker Compose or Kubernetes
- Enable SSL/TLS for all connections
- Configure firewall rules
- Regular automated backups
- Monitor with Prometheus/Grafana
- Use secrets management (Docker Secrets, K8s Secrets)
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

### v3.x (Current - Active Support)
- **Clean Architecture**: Security boundaries between layers
- **Event Sourcing**: Complete audit trail and state recovery
- **Docker-First**: Container isolation for all components
- **Enterprise Features**: JWT auth, structured logging, observability
- **Cross-Platform**: Tested on Windows, macOS, Linux, and WSL2
- **Zero Trust**: No implicit trust between services

### v2.8.x (Maintenance Support)
- Enhanced NLP processing requires additional dependencies
- Transformer models may consume significant memory
- Graph visualization runs client-side (secure)
- Security patches only, no new features
- Upgrade to v3.x recommended for production use

### v2.4.x (End of Life)
- Stable PostgreSQL + pgvector architecture
- Known security limitations
- No longer receiving updates
- Immediate upgrade to v3.x strongly recommended

## Resources

- [Project Documentation](README.md)
- [Architecture Overview](docs/ARCHITECTURE.md)
- [Testing Guide](docs/TESTING.md)
- [Deployment Guide](docs/deployment/DEPLOYMENT_V3.md)
- [Version History](CHANGELOG.md)
- [Release Notes v3.0.0](RELEASE_NOTES_v3.0.0.md)

---

**Last Updated**: January 27, 2025  
**Security Model**: Enterprise-Ready AI Memory System  
**Current Stable**: v3.0.0 | **Previous Stable**: v2.8.2  
**Support Matrix**: Active (3.x) | Maintenance (2.8.x) | EOL (2.4.x) | Unsupported (<2.3)