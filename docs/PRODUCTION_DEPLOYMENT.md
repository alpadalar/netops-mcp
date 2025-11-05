# Production Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying NetOps MCP in a production environment using Docker Compose.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Pre-Deployment Checklist](#pre-deployment-checklist)
- [Initial Setup](#initial-setup)
- [Configuration](#configuration)
- [Deployment](#deployment)
- [Monitoring](#monitoring)
- [Maintenance](#maintenance)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

- **Operating System**: Linux (Ubuntu 20.04+, Debian 11+, or similar)
- **Docker**: Version 20.10+
- **Docker Compose**: Version 2.0+
- **Memory**: Minimum 512MB, recommended 1GB+
- **CPU**: Minimum 1 core, recommended 2+ cores
- **Disk**: Minimum 2GB free space

### Network Requirements

- **Ports**: 8815 (or custom port) must be available
- **Firewall**: Configure to allow incoming connections on server port
- **DNS**: Ensure DNS resolution works for the server
- **Internet**: Required for pulling Docker images and system tools

### Access Requirements

- Root or sudo access for Docker operations
- Ability to configure firewall rules
- Access to create and manage SSL/TLS certificates (if using HTTPS)

## Pre-Deployment Checklist

- [ ] Server meets system requirements
- [ ] Docker and Docker Compose installed
- [ ] Firewall configured
- [ ] SSL/TLS certificates obtained (for HTTPS)
- [ ] API keys generated
- [ ] Configuration files prepared
- [ ] Backup strategy defined
- [ ] Monitoring solution selected

## Initial Setup

### 1. Install Docker

```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker

# Verify installation
docker --version
docker compose version
```

### 2. Clone Repository

```bash
git clone https://github.com/alpadalar/NetOpsMCP.git
cd NetOpsMCP
```

### 3. Generate API Keys

```bash
# Generate API keys
python scripts/generate_api_key.py -n 2 --config config/config.json

# Or manually generate and save
python scripts/generate_api_key.py -n 2 > api_keys.txt
```

**⚠️ Important**: Save these keys securely! They cannot be recovered.

## Configuration

### 1. Create Configuration File

```bash
# Copy example configuration
cp config/config.example.json config/config.json

# Edit configuration
nano config/config.json
```

### 2. Production Configuration

Edit `config/config.json`:

```json
{
  "logging": {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": "logs/netops-mcp.log"
  },
  "security": {
    "allow_privileged_commands": false,
    "allowed_hosts": ["your-domain.com"],
    "rate_limit_requests": 100,
    "rate_limit_window": 60,
    "require_auth": true,
    "api_keys": [
      "your-first-api-key-here",
      "your-second-api-key-here"
    ],
    "enable_cors": false,
    "cors_origins": ["https://your-frontend.com"]
  },
  "network": {
    "default_timeout": 30,
    "max_scan_timeout": 300,
    "allowed_ports": "1-65535"
  },
  "server": {
    "host": "0.0.0.0",
    "port": 8815,
    "path": "/netops-mcp"
  }
}
```

### 3. Environment Variables (Optional)

Create `.env` file for sensitive data:

```bash
cp env.production.example .env
nano .env
```

Edit `.env`:

```env
REQUIRE_AUTH=true
API_KEYS=key1,key2
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
```

### 4. Secure Configuration Files

```bash
# Restrict permissions
chmod 600 config/config.json
chmod 600 .env

# Ensure ownership
chown $USER:$USER config/config.json
chown $USER:$USER .env
```

## Deployment

### 1. Build and Start

```bash
# Build the Docker image
docker compose build

# Start the service
docker compose up -d

# Check status
docker compose ps
```

### 2. Verify Deployment

```bash
# Check health endpoint
curl http://localhost:8815/health

# Expected response:
# {
#   "status": "healthy",
#   "server": "NetOpsMCP-HTTP",
#   "mcp_tools": 26,
#   ...
# }
```

### 3. Test Authentication

```bash
# Test with valid API key
curl -X POST http://localhost:8815/netops-mcp \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"method": "system_status", "params": {}}'
```

### 4. Check Logs

```bash
# View application logs
docker compose logs -f netops-mcp

# View recent logs
docker compose logs --tail=100 netops-mcp

# Check log files
tail -f logs/netops-mcp.log
```

## Reverse Proxy Setup (HTTPS)

### Using Nginx

1. Install Nginx:

```bash
sudo apt-get update
sudo apt-get install nginx certbot python3-certbot-nginx
```

2. Create Nginx configuration (`/etc/nginx/sites-available/netops-mcp`):

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    # SSL configuration
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Proxy settings
    location / {
        proxy_pass http://localhost:8815;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts for long-running operations
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }
}
```

3. Enable configuration:

```bash
sudo ln -s /etc/nginx/sites-available/netops-mcp /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

4. Obtain SSL certificate:

```bash
sudo certbot --nginx -d your-domain.com
```

### Using Caddy

1. Install Caddy:

```bash
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install caddy
```

2. Create Caddyfile (`/etc/caddy/Caddyfile`):

```
your-domain.com {
    reverse_proxy localhost:8815
    
    # Security headers
    header {
        Strict-Transport-Security "max-age=31536000"
        X-Frame-Options "SAMEORIGIN"
        X-Content-Type-Options "nosniff"
        X-XSS-Protection "1; mode=block"
    }
}
```

3. Start Caddy:

```bash
sudo systemctl enable caddy
sudo systemctl start caddy
```

## Monitoring

### Application Logs

```bash
# Real-time logs
docker compose logs -f netops-mcp

# Filter for errors
docker compose logs netops-mcp | grep ERROR

# Save logs to file
docker compose logs --no-color netops-mcp > app-logs-$(date +%Y%m%d).log
```

### System Metrics

```bash
# Container stats
docker stats netops-mcp

# Disk usage
du -sh logs/
df -h
```

### Health Monitoring

Create a monitoring script (`/usr/local/bin/netops-health-check.sh`):

```bash
#!/bin/bash
HEALTH_URL="http://localhost:8815/health"
ALERT_EMAIL="admin@example.com"

response=$(curl -s -o /dev/null -w "%{http_code}" $HEALTH_URL)

if [ $response != "200" ]; then
    echo "NetOps MCP health check failed! HTTP $response" | \
        mail -s "NetOps MCP Alert" $ALERT_EMAIL
    exit 1
fi

exit 0
```

Add to crontab:

```bash
# Check every 5 minutes
*/5 * * * * /usr/local/bin/netops-health-check.sh
```

### Log Rotation

Configure log rotation (`/etc/logrotate.d/netops-mcp`):

```
/path/to/NetOpsMCP/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 netopsmcp netopsmcp
    sharedscripts
    postrotate
        docker compose -f /path/to/NetOpsMCP/docker-compose.yml restart netops-mcp
    endscript
}
```

## Maintenance

### Regular Updates

```bash
# Pull latest code
git pull origin main

# Rebuild and restart
docker compose down
docker compose build
docker compose up -d

# Verify
curl http://localhost:8815/health
```

### Backup

```bash
#!/bin/bash
# backup-netops.sh

BACKUP_DIR="/backups/netops-mcp"
DATE=$(date +%Y%m%d-%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup configuration
tar -czf $BACKUP_DIR/config-$DATE.tar.gz config/

# Backup logs
tar -czf $BACKUP_DIR/logs-$DATE.tar.gz logs/

# Keep only last 30 days
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete

echo "Backup completed: $DATE"
```

Schedule backup:

```bash
# Daily at 2 AM
0 2 * * * /usr/local/bin/backup-netops.sh
```

### Security Updates

```bash
# Update system packages
sudo apt-get update && sudo apt-get upgrade -y

# Update Docker images
docker compose pull
docker compose up -d

# Check for vulnerabilities
docker scan netops-mcp:latest
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker compose logs netops-mcp

# Check Docker status
docker compose ps

# Restart services
docker compose restart

# Full reset
docker compose down
docker compose up -d
```

### Authentication Issues

```bash
# Verify API keys in config
cat config/config.json | grep -A 5 api_keys

# Check authentication logs
docker compose logs netops-mcp | grep -i auth

# Test without authentication (temporarily)
# Set require_auth: false in config.json
```

### Performance Issues

```bash
# Check resource usage
docker stats netops-mcp

# Increase limits in docker-compose.yml:
deploy:
  resources:
    limits:
      cpus: '4.0'
      memory: 2G
```

### Network Tools Not Working

```bash
# Verify capabilities
docker inspect netops-mcp | grep -i cap

# Check if running as non-root
docker exec netops-mcp whoami

# Test specific tool
docker exec netops-mcp ping -c 4 google.com
```

### Port Already in Use

```bash
# Find process using port
sudo lsof -i :8815

# Change port in config and restart
# Edit config/config.json: "port": 8816
```

## Best Practices

1. **Always use HTTPS in production**
2. **Enable authentication**
3. **Use strong API keys**
4. **Configure rate limiting**
5. **Monitor logs regularly**
6. **Keep system updated**
7. **Regular backups**
8. **Use firewall rules**
9. **Limit network exposure**
10. **Document your setup**

## Support

For issues or questions:
- Documentation: https://github.com/alpadalar/NetOpsMCP#readme
- Issues: https://github.com/alpadalar/NetOpsMCP/issues
- Email: alp.adalar@gmail.com

## Next Steps

After successful deployment:

1. Configure monitoring and alerts
2. Set up log aggregation
3. Implement backup automation
4. Document your deployment
5. Train team on usage
6. Create runbooks for common issues
7. Plan for disaster recovery

## Additional Resources

- [API Authentication Guide](API_AUTHENTICATION.md)
- [Security Policy](../SECURITY.md)
- [README](../README.md)
- [README (Türkçe)](../README.tr.md)






