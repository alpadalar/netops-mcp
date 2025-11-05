# Security Policy

## Supported Versions

We release patches for security vulnerabilities for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability, please send an email to alp.adalar@gmail.com. All security vulnerabilities will be promptly addressed.

**Please do not report security vulnerabilities through public GitHub issues.**

### What to Include

When reporting a vulnerability, please include:

- Type of vulnerability
- Full paths of source file(s) related to the manifestation of the issue
- The location of the affected source code (tag/branch/commit or direct URL)
- Any special configuration required to reproduce the issue
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the issue, including how an attacker might exploit it

## Security Best Practices

### Authentication

1. **API Keys**: Always use strong, randomly generated API keys
   - Use the provided script: `python scripts/generate_api_key.py`
   - Never commit API keys to version control
   - Rotate API keys regularly

2. **Environment Variables**: Store sensitive data in environment variables, not in config files
   - Use `env.production.example` as a template
   - Never commit `.env` files

3. **HTTPS**: Always use HTTPS in production
   - Use a reverse proxy (nginx, Caddy) with SSL/TLS
   - Never expose the application directly to the internet

### Network Security

1. **Firewall Rules**: Configure appropriate firewall rules
   - Only allow necessary ports (8815 or your custom port)
   - Restrict access by IP address when possible

2. **Rate Limiting**: Configure appropriate rate limits
   - Default: 100 requests per 60 seconds
   - Adjust based on your use case

3. **Network Scanning**: Be aware of legal implications
   - Only scan networks you own or have permission to scan
   - Some network scanning activities may be illegal in your jurisdiction

### Docker Security

1. **Non-Root User**: The application runs as a non-root user
   - User ID: 1000 (netopsmcp)
   - Limited privileges

2. **Capabilities**: Only required capabilities are granted
   - `NET_ADMIN`: For network configuration
   - `NET_RAW`: For raw packet operations (ping, traceroute)

3. **Resource Limits**: Set appropriate resource limits
   - CPU: 2 cores maximum
   - Memory: 1GB maximum

4. **Image Scanning**: Regularly scan Docker images
   - Use Trivy or similar tools
   - Update base images regularly

### Input Validation

All user inputs are validated to prevent:
- Command injection attacks
- Path traversal attacks
- Invalid network parameters
- Malformed URLs and domains

### Logging and Monitoring

1. **Structured Logging**: All requests and errors are logged
   - Review logs regularly
   - Monitor for suspicious activity

2. **Metrics**: Monitor application metrics
   - Request rates
   - Error rates
   - Authentication failures

3. **Alerts**: Set up alerts for:
   - High error rates
   - Authentication failures
   - Rate limit violations

## Known Security Considerations

### Privileged Network Operations

Some network diagnostic tools require elevated privileges:
- **ping**: Requires `CAP_NET_RAW` capability
- **traceroute**: Requires `CAP_NET_RAW` capability
- **nmap**: May require additional privileges for certain scan types
- **arping**: Requires `CAP_NET_RAW` capability

**Mitigation**: Docker container runs with minimal required capabilities (`NET_ADMIN`, `NET_RAW`) instead of full privileged mode.

### Network Scanning Legal Issues

Network scanning tools can be used for malicious purposes:
- Port scanning may be interpreted as hostile activity
- Some jurisdictions have laws against unauthorized network scanning
- ISPs may have acceptable use policies that prohibit scanning

**Mitigation**: 
- Document and communicate intended use
- Only scan networks you own or have explicit permission to scan
- Implement logging and audit trails

### Command Execution

The application executes system commands:
- All inputs are validated and sanitized
- Command injection patterns are detected and blocked
- Commands run with limited user privileges

**Mitigation**: Input validation is implemented at multiple layers.

## Security Updates

### Automated Scanning

- **GitHub Actions**: Automated security scanning on every push
- **Trivy**: Container image vulnerability scanning
- **Bandit**: Python security linter
- **Safety**: Dependency vulnerability checking

### Manual Updates

Check for security updates regularly:

```bash
# Update dependencies
uv pip list --outdated

# Security audit
safety check

# Scan for vulnerabilities
bandit -r src/
```

## Secure Deployment Checklist

- [ ] Enable authentication (`require_auth: true`)
- [ ] Generate and configure strong API keys
- [ ] Use environment variables for secrets
- [ ] Configure HTTPS/TLS with reverse proxy
- [ ] Set up firewall rules
- [ ] Configure rate limiting
- [ ] Enable CORS only for trusted origins
- [ ] Set resource limits
- [ ] Configure logging and monitoring
- [ ] Regular security updates
- [ ] Regular log review
- [ ] Backup configuration and logs

## Contact

For security concerns, please contact:
- Email: alp.adalar@gmail.com
- GitHub: @alpadalar

## Attribution

This security policy is based on industry best practices and adapted for NetOps MCP.






