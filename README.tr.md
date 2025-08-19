# NetOps MCP - Network Operations Araçları MCP Sunucusu

Temel network operations ve infrastructure araçlarına standartlaştırılmış bir arayüz üzerinden erişim sağlayan kapsamlı Model Context Protocol (MCP) sunucusu.

## 🚀 Özellikler

### Ağ Bağlantı Araçları
- **Ping**: Özelleştirilebilir paket sayısı ve zaman aşımı ile host bağlantısını test et
- **Traceroute**: Yapılandırılabilir maksimum hop ile ağ yolunu izle
- **MTR**: Gerçek zamanlı istatistiklerle ağ yolunu izle
- **Telnet**: Telnet kullanarak port bağlantısını test et
- **Netcat**: Netcat kullanarak port bağlantısını test et

### HTTP/API Test Araçları
- **cURL**: Header, method ve veri üzerinde tam kontrol ile HTTP istekleri çalıştır
- **HTTPie**: Basitleştirilmiş sözdizimi ile alternatif HTTP istemcisi
- **API Test**: Beklenen durum kodları ile API endpoint'lerini doğrula

### DNS Araçları
- **nslookup**: Çeşitli kayıt türleri ile DNS sorguları
- **dig**: Gelişmiş DNS sorgulama aracı
- **host**: Basit DNS arama yardımcı programı

### Ağ Keşif Araçları
- **Nmap**: Ağ tarama ve servis numaralandırma
- **Port Tarama**: Hedefli port tarama yetenekleri
- **Servis Keşfi**: Hedeflerde çalışan servisleri tanımla

### Sistem İzleme Araçları
- **SS**: Soket istatistikleri ve bağlantı izleme
- **Netstat**: Ağ istatistikleri ve bağlantı bilgileri
- **ARP**: Adres Çözümleme Protokolü tablosu yönetimi
- **ARPing**: ARP bağlantısını test et

### Sistem Bilgi Araçları
- **Sistem Durumu**: CPU, bellek ve disk kullanımı izleme
- **İşlem Listesi**: Çalışan işlemlerin numaralandırılması
- **Gerekli Araçlar Kontrolü**: Sistem aracı kullanılabilirliğini doğrula

## 📋 Gereksinimler

### Gerekli Sistem Araçları
Aşağıdaki araçlar sistemde kurulu olmalıdır:

```bash
# Ağ araçları
curl, ping, traceroute, mtr, telnet, nc (netcat)

# DNS araçları
nslookup, dig, host

# Ağ keşif
nmap

# Sistem araçları
ss, netstat, arp, arping

# HTTP araçları
httpie (isteğe bağlı, gelişmiş HTTP testi için)
```

### Python Gereksinimleri
- Python 3.8+
- uv paket yöneticisi (önerilen)

## 🛠️ Kurulum

### uv Kullanarak (Önerilen)

```bash
# Depoyu klonla
git clone <repository-url>
cd NetOpsMCP

# uv kullanarak bağımlılıkları kur
uv venv
source .venv/bin/activate  # Windows'ta: .venv\Scripts\activate
uv pip install -e ".[dev]"
```

### pip Kullanarak

```bash
# Depoyu klonla
git clone <repository-url>
cd NetOpsMCP

# Sanal ortam oluştur
python -m venv .venv
source .venv/bin/activate  # Windows'ta: .venv\Scripts\activate

# Bağımlılıkları kur
pip install -e ".[dev]"
```

### Docker Kullanarak

```bash
# Docker Compose ile build et ve çalıştır
docker compose up -d

# Veya manuel olarak build et
docker build -t netopsmcp .
docker run -p 8815:8815 netopsmcp
```

## 🚀 Hızlı Başlangıç

### 1. Sunucuyu Başlat

```bash
# Python ile doğrudan
python -m src.devops_mcp.server_http --host 0.0.0.0 --port 8815

# Docker ile
docker compose up -d

# Sağlanan script ile
./start_http_server.sh
```

### 2. Sunucuyu Test Et

```bash
# Sağlık kontrolü
curl http://localhost:8815/devops-mcp/health

# Sistem gereksinimlerini test et
curl -X POST http://localhost:8815/devops-mcp \
  -H "Content-Type: application/json" \
  -d '{"method": "check_required_tools", "params": {}}'
```

### 3. Örnek Kullanım

```python
# Bir host'a ping at
result = ping_host("google.com", count=4, timeout=10)

# HTTP endpoint'ini test et
result = curl_request("https://httpbin.org/get", method="GET")

# DNS araması
result = nslookup_query("google.com", record_type="A")

# Ağ taraması
result = nmap_scan("192.168.1.1", ports="1-1000", scan_type="basic")
```

## 📖 API Referansı

### Ağ Bağlantısı

#### `ping_host(host: str, count: int = 4, timeout: int = 10)`
Ping kullanarak bir host'a bağlantıyı test et.

**Parametreler:**
- `host`: Hedef host adı veya IP adresi
- `count`: Ping paket sayısı (varsayılan: 4)
- `timeout`: Saniye cinsinden zaman aşımı (varsayılan: 10)

**Döner:** Ping istatistikleri ve sonuçları

#### `traceroute_path(target: str, max_hops: int = 30, timeout: int = 30)`
Bir hedefe ağ yolunu izle.

**Parametreler:**
- `target`: Hedef host adı veya IP adresi
- `max_hops`: Maksimum hop sayısı (varsayılan: 30)
- `timeout`: Saniye cinsinden zaman aşımı (varsayılan: 30)

**Döner:** Ağ yolu bilgileri

#### `mtr_monitor(target: str, count: int = 10, timeout: int = 30)`
MTR kullanarak ağ yolunu izle.

**Parametreler:**
- `target`: Hedef host adı veya IP adresi
- `count`: Sonda sayısı (varsayılan: 10)
- `timeout`: Saniye cinsinden zaman aşımı (varsayılan: 30)

**Döner:** MTR istatistikleri ve hop bilgileri

### HTTP Testi

#### `curl_request(url: str, method: str = "GET", headers: dict = None, data: dict = None, timeout: int = 30)`
cURL kullanarak HTTP isteği çalıştır.

**Parametreler:**
- `url`: Hedef URL
- `method`: HTTP metodu (GET, POST, PUT, DELETE, PATCH)
- `headers`: HTTP header'ları sözlüğü
- `data`: POST/PUT istekleri için istek verisi
- `timeout`: Saniye cinsinden istek zaman aşımı

**Döner:** HTTP yanıtı ve zamanlama bilgileri

#### `httpie_request(url: str, method: str = "GET", headers: dict = None, data: dict = None, timeout: int = 30)`
HTTPie kullanarak HTTP isteği çalıştır.

**Parametreler:** curl_request ile aynı

**Döner:** HTTP yanıtı ve zamanlama bilgileri

### DNS Araçları

#### `nslookup_query(domain: str, record_type: str = "A", server: str = None)`
nslookup kullanarak DNS kayıtlarını sorgula.

**Parametreler:**
- `domain`: Hedef domain adı
- `record_type`: DNS kayıt türü (A, AAAA, MX, NS, TXT, CNAME)
- `server`: Özel DNS sunucusu (isteğe bağlı)

**Döner:** DNS sorgu sonuçları

#### `dig_query(domain: str, record_type: str = "A", server: str = None)`
dig kullanarak DNS kayıtlarını sorgula.

**Parametreler:** nslookup_query ile aynı

**Döner:** Detaylı DNS sorgu sonuçları

### Ağ Keşfi

#### `nmap_scan(target: str, ports: str = None, scan_type: str = "basic", timeout: int = 300)`
nmap kullanarak ağı tara.

**Parametreler:**
- `target`: Hedef host adı, IP veya ağ aralığı
- `ports`: Port aralığı (örn., "1-1000", "80,443,8080")
- `scan_type`: Tarama türü (basic, full, stealth)
- `timeout`: Saniye cinsinden tarama zaman aşımı

**Döner:** Ağ tarama sonuçları

#### `port_scan(target: str, ports: str, timeout: int = 60)`
Hedefli port taraması gerçekleştir.

**Parametreler:**
- `target`: Hedef host adı veya IP adresi
- `ports`: Taranacak port aralığı
- `timeout`: Saniye cinsinden tarama zaman aşımı

**Döner:** Port tarama sonuçları

### Sistem İzleme

#### `system_status()`
Sistem durumu bilgilerini al.

**Döner:** CPU, bellek ve disk kullanım istatistikleri

#### `ss_connections(state: str = None, protocol: str = None)`
ss kullanarak ağ bağlantılarını göster.

**Parametreler:**
- `state`: Bağlantı durumuna göre filtrele
- `protocol`: Protokole göre filtrele

**Döner:** Ağ bağlantı bilgileri

#### `netstat_connections(state: str = None, protocol: str = None)`
netstat kullanarak ağ bağlantılarını göster.

**Parametreler:** ss_connections ile aynı

**Döner:** Ağ bağlantı bilgileri

## 🧪 Test

### Tüm Testleri Çalıştır

```bash
# pytest kullanarak
pytest tests/ -v

# uv kullanarak
uv run pytest tests/ -v

# Kapsam ile
pytest tests/ --cov=src --cov-report=html
```

### Test Kategorileri

- **Birim Testleri**: Bireysel araç işlevselliği
- **Entegrasyon Testleri**: Uçtan uca iş akışı testi
- **Mock Testleri**: Komut yürütme simülasyonu
- **Doğrulama Testleri**: Girdi doğrulama ve hata işleme

### Test Kapsamı

Test paketi şunları kapsar:
- ✅ Tüm araç metodları ve işlevselliği
- ✅ Girdi doğrulama ve hata işleme
- ✅ Komut yürütme ve çıktı ayrıştırma
- ✅ Uç durumlar ve hata senaryoları
- ✅ Harici bağımlılıklar için mock testi

## 🔧 Yapılandırma

### Ortam Değişkenleri

```bash
# Sunucu yapılandırması
DEVOPSCP_HOST=0.0.0.0
DEVOPSCP_PORT=8815
DEVOPSCP_LOG_LEVEL=INFO

# Araç zaman aşımları
PING_TIMEOUT=10
TRACEROUTE_TIMEOUT=30
MTR_TIMEOUT=30
CURL_TIMEOUT=30
NMAP_TIMEOUT=300
```

### Yapılandırma Dosyası

`config/config.json` oluştur:

```json
{
  "server": {
    "host": "0.0.0.0",
    "port": 8815,
    "log_level": "INFO"
  },
  "tools": {
    "timeouts": {
      "ping": 10,
      "traceroute": 30,
      "mtr": 30,
      "curl": 30,
      "nmap": 300
    },
    "defaults": {
      "ping_count": 4,
      "traceroute_max_hops": 30,
      "mtr_count": 10
    }
  }
}
```

## 🐳 Docker Desteği

### Docker Compose

```yaml
version: '3.8'
services:
  devopsmcp:
    build: .
    ports:
      - "8815:8815"
    environment:
      - DEVOPSCP_HOST=0.0.0.0
      - DEVOPSCP_PORT=8815
    volumes:
      - ./logs:/app/logs
      - ./config:/app/config
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8815/devops-mcp/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Docker Build

```bash
# Image build et
docker build -t devopsmcp .

# Container çalıştır
docker run -d \
  --name devopsmcp \
  -p 8815:8815 \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/config:/app/config \
  devopsmcp
```

## 📊 İzleme ve Günlük

### Günlük Seviyeleri

- **DEBUG**: Detaylı hata ayıklama bilgileri
- **INFO**: Genel operasyonel mesajlar
- **WARNING**: Potansiyel sorunlar için uyarı mesajları
- **ERROR**: Başarısız işlemler için hata mesajları

### Günlük Dosyaları

- `logs/devopsmcp.log`: Ana uygulama günlüğü
- `logs/access.log`: HTTP erişim günlüğü
- `logs/error.log`: Hata günlüğü

### Sağlık Kontrolleri

```bash
# Sunucu sağlığını kontrol et
curl http://localhost:8815/devops-mcp/health

# Sistem gereksinimlerini kontrol et
curl -X POST http://localhost:8815/devops-mcp \
  -H "Content-Type: application/json" \
  -d '{"method": "check_required_tools", "params": {}}'
```

## 🔒 Güvenlik Hususları

### Ağ Güvenliği

- **Güvenlik Duvarı Kuralları**: Sunucu portu için uygun güvenlik duvarı kuralları yapılandır
- **Erişim Kontrolü**: Gerekirse kimlik doğrulama uygula
- **Ağ İzolasyonu**: Mümkün olduğunda izole ağ ortamlarında çalıştır

### Araç Güvenliği

- **Ayrıcalıklı İşlemler**: Bazı araçlar yükseltilmiş ayrıcalıklar gerektirir
- **Ağ Tarama**: Ağ taramanın yasal etkilerinin farkında ol
- **Hız Sınırlama**: Kaynak yoğun işlemler için hız sınırlama uygula

### En İyi Uygulamalar

- **Girdi Doğrulama**: Tüm girdiler işlenmeden önce doğrulanır
- **Hata İşleme**: Kapsamlı hata işleme ve günlük tutma
- **Zaman Aşımı Yönetimi**: Tüm işlemler için yapılandırılabilir zaman aşımları
- **Kaynak Limitleri**: Yerleşik kaynak kullanım limitleri

## 🤝 Katkıda Bulunma

### Geliştirme Kurulumu

```bash
# Depoyu klonla
git clone <repository-url>
cd DevOpsMCP

# Geliştirme bağımlılıklarını kur
uv pip install -e ".[dev]"

# Pre-commit hook'larını kur
pre-commit install

# Testleri çalıştır
pytest tests/ -v
```

### Kod Stili

- **Black**: Kod formatlama
- **isort**: Import sıralama
- **flake8**: Linting
- **mypy**: Tip kontrolü

### Test Yönergeleri

- Tüm yeni işlevsellik için test yaz
- Test kapsamını %90'ın üzerinde tut
- Anlamlı test adları ve açıklamaları kullan
- Harici bağımlılıkları mock'la

### Pull Request Süreci

1. Depoyu fork et
2. Özellik dalı oluştur
3. Değişikliklerini yap
4. Yeni işlevsellik için test ekle
5. Dokümantasyonu güncelle
6. Pull request gönder

## 📄 Lisans

Bu proje MIT Lisansı altında lisanslanmıştır - detaylar için [LICENSE](LICENSE) dosyasına bakın.

## 🆘 Destek

### Dokümantasyon

- [API Referansı](docs/api.md)
- [Yapılandırma Kılavuzu](docs/configuration.md)
- [Sorun Giderme](docs/troubleshooting.md)

### Sorunlar

- **Hata Raporları**: GitHub Issues kullan
- **Özellik İstekleri**: GitHub Issues üzerinden gönder
- **Güvenlik Sorunları**: Doğrudan bakımcılarla iletişime geç

### Topluluk

- **Tartışmalar**: GitHub Discussions
- **Wiki**: Ek dokümantasyon için Proje Wiki'si

## 🙏 Teşekkürler

- **MCP Protokolü**: Model Context Protocol özelliği
- **Ağ Araçları**: Açık kaynak ağ yardımcı programları
- **Test Framework**: pytest ve ilgili araçlar
- **Topluluk**: Katkıda bulunanlar ve kullanıcılar

---

**NetOps MCP** - Standartlaştırılmış araç erişimi ile network operations iş akışlarını güçlendirme.
