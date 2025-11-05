# API Authentication Guide

## Overview

NetOps MCP supports API key-based authentication to secure access to network diagnostic tools. This guide explains how to configure and use authentication.

## Table of Contents

- [Generating API Keys](#generating-api-keys)
- [Configuring Authentication](#configuring-authentication)
- [Making Authenticated Requests](#making-authenticated-requests)
- [API Key Management](#api-key-management)
- [Security Best Practices](#security-best-practices)

## Generating API Keys

### Using the Generation Script

The easiest way to generate secure API keys is using the provided script:

```bash
# Generate a single API key
python scripts/generate_api_key.py

# Generate multiple API keys
python scripts/generate_api_key.py -n 3

# Generate and add to config file
python scripts/generate_api_key.py --config config/config.json

# Generate with JSON output
python scripts/generate_api_key.py --json

# Generate with hashed versions
python scripts/generate_api_key.py --hash
```

### Manual Generation

You can also generate API keys programmatically:

```python
from netops_mcp.middleware.auth import generate_api_key, hash_api_key

# Generate a new API key
api_key = generate_api_key(length=32)
print(f"API Key: {api_key}")

# Generate hash for storage
api_key_hash = hash_api_key(api_key)
print(f"Hash: {api_key_hash}")
```

## Configuring Authentication

### Configuration File

Edit your `config/config.json`:

```json
{
  "security": {
    "require_auth": true,
    "api_keys": [
      "your-generated-api-key-here",
      "another-api-key-for-different-client"
    ],
    "rate_limit_requests": 100,
    "rate_limit_window": 60
  }
}
```

### Environment Variables

Alternatively, use environment variables:

```bash
# Enable authentication
export REQUIRE_AUTH=true

# Set API keys (comma-separated)
export API_KEYS=key1,key2,key3
```

### Docker Compose

In your `docker-compose.yml`:

```yaml
services:
  netops-mcp:
    environment:
      - REQUIRE_AUTH=true
      - API_KEYS=${API_KEYS}
```

Then create a `.env` file:

```env
API_KEYS=your-api-key-here
```

## Making Authenticated Requests

### Using Bearer Token

The recommended method is to use the `Authorization` header with a Bearer token:

```bash
curl -X POST http://localhost:8815/netops-mcp \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"method": "ping_host", "params": {"host": "google.com"}}'
```

### Using X-API-Key Header

Alternatively, use the `X-API-Key` header:

```bash
curl -X POST http://localhost:8815/netops-mcp \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"method": "ping_host", "params": {"host": "google.com"}}'
```

### Using API-Key Header

Another option is the `API-Key` header:

```bash
curl -X POST http://localhost:8815/netops-mcp \
  -H "API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"method": "ping_host", "params": {"host": "google.com"}}'
```

## Python Client Examples

### Using requests

```python
import requests

API_KEY = "your-api-key-here"
BASE_URL = "http://localhost:8815/netops-mcp"

# Using Bearer token
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

response = requests.post(
    BASE_URL,
    headers=headers,
    json={
        "method": "ping_host",
        "params": {
            "host": "google.com",
            "count": 4
        }
    }
)

print(response.json())
```

### Using httpx

```python
import httpx

API_KEY = "your-api-key-here"
BASE_URL = "http://localhost:8815/netops-mcp"

async with httpx.AsyncClient() as client:
    response = await client.post(
        BASE_URL,
        headers={"Authorization": f"Bearer {API_KEY}"},
        json={
            "method": "traceroute_path",
            "params": {"target": "google.com"}
        }
    )
    print(response.json())
```

## API Key Management

### Multiple API Keys

You can configure multiple API keys for different clients or purposes:

```json
{
  "security": {
    "api_keys": [
      "production-app-key-xxxx",
      "monitoring-service-key-yyyy",
      "development-key-zzzz"
    ]
  }
}
```

### Key Rotation

Best practice is to rotate API keys regularly:

1. Generate a new API key:
   ```bash
   python scripts/generate_api_key.py
   ```

2. Add the new key to your configuration (keep old key temporarily):
   ```json
   {
     "security": {
       "api_keys": [
         "old-key",
         "new-key"
       ]
     }
   }
   ```

3. Update all clients to use the new key

4. Remove the old key from configuration:
   ```json
   {
     "security": {
       "api_keys": [
         "new-key"
       ]
     }
   }
   ```

5. Restart the server

### Revoking Keys

To revoke an API key, simply remove it from the configuration and restart the server:

```json
{
  "security": {
    "api_keys": [
      "still-valid-key"
    ]
  }
}
```

## Error Responses

### No API Key Provided

```json
{
  "error": "Authentication required",
  "message": "Please provide an API key using Authorization header (Bearer token) or X-API-Key header"
}
```

HTTP Status: `401 Unauthorized`

### Invalid API Key

```json
{
  "error": "Invalid API key",
  "message": "The provided API key is not valid"
}
```

HTTP Status: `403 Forbidden`

## Exempt Endpoints

Some endpoints do not require authentication:

- `/health` - Health check endpoint
- `/metrics` - Prometheus metrics endpoint (if enabled)

These endpoints can be accessed without an API key:

```bash
curl http://localhost:8815/health
```

## Security Best Practices

### Key Storage

1. **Never commit API keys to version control**
   - Add `.env` to `.gitignore`
   - Use environment variables or secret management systems

2. **Use strong, randomly generated keys**
   - Minimum 32 characters
   - Use the provided generation script

3. **Store keys securely**
   - Use secret management systems (HashiCorp Vault, AWS Secrets Manager)
   - Encrypt configuration files if stored in version control
   - Restrict file permissions: `chmod 600 config/config.json`

### Key Usage

1. **One key per client/application**
   - Easier to track usage
   - Easier to revoke if compromised

2. **Rotate keys regularly**
   - Every 90 days recommended
   - Immediately if compromised

3. **Monitor authentication failures**
   - Set up alerts for repeated failures
   - May indicate brute force attempts

### Network Security

1. **Always use HTTPS in production**
   - API keys sent over plain HTTP can be intercepted

2. **Use a reverse proxy**
   - nginx, Caddy, or Traefik
   - Handle SSL/TLS termination

3. **Implement rate limiting**
   - Already configured by default
   - Adjust based on your needs

## Testing Authentication

### Test Valid Key

```bash
# This should succeed
curl -X POST http://localhost:8815/netops-mcp \
  -H "Authorization: Bearer YOUR_VALID_KEY" \
  -H "Content-Type: application/json" \
  -d '{"method": "system_status", "params": {}}'
```

### Test Invalid Key

```bash
# This should return 403 Forbidden
curl -X POST http://localhost:8815/netops-mcp \
  -H "Authorization: Bearer INVALID_KEY" \
  -H "Content-Type: application/json" \
  -d '{"method": "system_status", "params": {}}'
```

### Test No Key

```bash
# This should return 401 Unauthorized
curl -X POST http://localhost:8815/netops-mcp \
  -H "Content-Type: application/json" \
  -d '{"method": "system_status", "params": {}}'
```

## Troubleshooting

### Authentication Not Working

1. Check that authentication is enabled:
   ```json
   {
     "security": {
       "require_auth": true
     }
   }
   ```

2. Verify API key is in configuration:
   ```bash
   cat config/config.json | grep -A 5 security
   ```

3. Check server logs:
   ```bash
   tail -f logs/netops-mcp.log
   ```

4. Verify header format:
   ```bash
   # Correct
   Authorization: Bearer YOUR_KEY
   
   # Incorrect
   Authorization: YOUR_KEY
   ```

### Key Not Recognized

1. Ensure key matches exactly (no extra spaces)
2. Check for special characters or encoding issues
3. Verify server was restarted after configuration change

## Support

For authentication issues or questions:
- GitHub Issues: https://github.com/alpadalar/NetOpsMCP/issues
- Email: alp.adalar@gmail.com






