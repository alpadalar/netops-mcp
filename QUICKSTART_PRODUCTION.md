# NetOps MCP - Production Deployment Hızlı Başlangıç

## 🚀 5 Dakikada Production'a Alın

### 1. API Keys Oluşturun

```bash
python scripts/generate_api_key.py -n 2 --config config/config.json
```

**Önemli**: Üretilen anahtarları güvenli bir yerde saklayın!

### 2. Konfigürasyonu Kontrol Edin

```bash
cat config/config.json
```

Şunların doğru olduğundan emin olun:
- `require_auth: true`
- `api_keys` listesi dolu
- `rate_limit_requests` ayarlanmış

### 3. Docker ile Deploy Edin

```bash
# Container'ı başlat
docker compose up -d

# Status kontrol et
docker compose ps

# Log'ları kontrol et
docker compose logs -f netops-mcp
```

### 4. Deployment'ı Test Edin

```bash
# Health check
curl http://localhost:8815/health

# API key ile test request
curl -X POST http://localhost:8815/netops-mcp \
  -H "Authorization: Bearer YOUR_API_KEY_HERE" \
  -H "Content-Type: application/json" \
  -d '{"method": "system_status", "params": {}}'
```

### 5. (Opsiyonel) HTTPS Kurulumu

#### Nginx ile:

```bash
# Nginx kur
sudo apt-get install nginx certbot python3-certbot-nginx

# Certificate al
sudo certbot --nginx -d yourdomain.com

# Nginx config'i /etc/nginx/sites-available/netops-mcp dosyasına ekleyin
```

#### Caddy ile (daha kolay):

```bash
# Caddy kur
sudo apt install caddy

# /etc/caddy/Caddyfile düzenle
echo "yourdomain.com {
    reverse_proxy localhost:8815
}" | sudo tee /etc/caddy/Caddyfile

# Caddy'yi başlat
sudo systemctl start caddy
```

## ✅ Production Checklist

- [x] **Authentication**: API key authentication etkin
- [x] **Rate Limiting**: 100 req/min default limit
- [x] **Input Validation**: Tüm girdiler sanitize ediliyor
- [x] **Docker Security**: Non-root user, minimal capabilities
- [x] **Logging**: Structured logging hazır
- [x] **Metrics**: Prometheus metrics `/metrics` endpoint'inde
- [x] **Health Checks**: `/health` endpoint çalışıyor
- [x] **CI/CD**: GitHub Actions workflows hazır
- [ ] **HTTPS**: Reverse proxy kurulumu yapılmalı
- [ ] **Monitoring**: Log monitoring ve alerting kurulmalı
- [ ] **Backup**: Config ve log backup stratejisi belirlenmeli

## 🔐 Güvenlik En İyi Uygulamaları

1. **API Keys**: API key'leri asla commit etmeyin
2. **HTTPS**: Production'da mutlaka HTTPS kullanın
3. **Firewall**: Sadece gerekli portları açık tutun
4. **Updates**: Düzenli güvenlik güncellemeleri yapın
5. **Monitoring**: Log'ları düzenli kontrol edin

## 📊 Monitoring

```bash
# Real-time logs
docker compose logs -f netops-mcp

# Metrics endpoint
curl http://localhost:8815/metrics

# Health status
curl http://localhost:8815/health | jq
```

## 🔄 Güncelleme

```bash
# Yeni versiyonu pull et
git pull origin main

# Container'ı yeniden başlat
docker compose down
docker compose build
docker compose up -d
```

## 🆘 Sorun Giderme

### Container başlamıyor
```bash
docker compose logs netops-mcp
docker compose restart
```

### Authentication çalışmıyor
```bash
# Config'i kontrol et
cat config/config.json | grep -A 5 security

# API key'i test et
curl -I http://localhost:8815/netops-mcp \
  -H "Authorization: Bearer YOUR_KEY"
```

### Port kullanımda
```bash
# Portu kullanan process'i bul
sudo lsof -i :8815

# Config'de farklı port kullan
# config/config.json içinde "port": 8816
```

## 📚 Detaylı Dokümantasyon

- [Production Deployment Guide](docs/PRODUCTION_DEPLOYMENT.md)
- [API Authentication](docs/API_AUTHENTICATION.md)
- [Security Policy](SECURITY.md)
- [README](README.md)
- [README (Türkçe)](README.tr.md)

## 🎯 Sonraki Adımlar

1. ✅ API keys oluştur ve test et
2. ✅ Health check'i doğrula
3. ✅ Metrics'i kontrol et
4. 🔲 HTTPS kurulumu yap
5. 🔲 Monitoring ve alerting kur
6. 🔲 Backup automation'u yapılandır
7. 🔲 Production monitoring dashboard oluştur

## 💬 Destek

- GitHub: https://github.com/alpadalar/NetOpsMCP
- Issues: https://github.com/alpadalar/NetOpsMCP/issues
- Email: alp.adalar@gmail.com

---

**NetOps MCP** - Production-Ready Network Operations Platform 🚀







