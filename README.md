# 🔄 IP Rotator Pro

**All-in-one Proxy Scraper, Validator & Rotator** — Scrape thousands of fresh proxies, validate them instantly, rotate IPs automatically, and stay anonymous. GitHub-ready. Termux-compatible.

![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20Termux-orange)

```
  ___  ____    ____        _        _
 |_ _||  _ \  |  _ \  ___ | |_  __ _| |_  ___  _ __
  | | | |_) | | |_) |/ _ \| __|/ _` | __|/ _ \| '__|
  | | |  __/  |  _ <| (_) | |_| (_| | |_| (_) | |
 |___||_|     |_| \_\\___/ \__|\__,_|\__|\___/|_|
```

## ⚡ Features

| Feature | Description |
|---------|-------------|
| 🌐 **Multi-Source Scraping** | Scrape from 10+ free proxy sources (30+ endpoints) |
| ⚡ **Async Validation** | Validate 100+ proxies concurrently — blazing fast |
| 💀 **Dead IP Detection** | Auto-detect and remove non-working proxies |
| 🔄 **Auto-Refresh** | Background daemon refreshes pool every 3 minutes |
| 🎯 **Smart Rotation** | 4 strategies: Round-Robin, Random, Smart, Fastest |
| 🌍 **Protocol Support** | HTTP, HTTPS, SOCKS4, SOCKS5 |
| 🔒 **Anonymity Detection** | Detect: Transparent, Anonymous, Elite proxies |
| 🚀 **Local Proxy Server** | HTTP gateway on localhost — auto-rotates per request |
| 📊 **Rich CLI Dashboard** | Beautiful terminal UI with live stats |
| 📁 **Multi-Format Export** | Export to TXT, CSV, JSON |
| 🌎 **Country Filter** | Filter proxies by country code |
| ⏱️ **Speed Testing** | Measure latency, sort by fastest |

## 🚀 Quick Start

### Installation (PC — Windows/Linux/Mac)

```bash
# Clone the repo
git clone https://github.com/your-username/ip-rotator-pro.git
cd ip-rotator-pro

# Install dependencies
pip install -r requirements.txt

# Run!
python rotator.py run
```

### Installation (Termux — Android)

```bash
# Install Python
pkg install python git

# Clone and install
git clone https://github.com/your-username/ip-rotator-pro.git
cd ip-rotator-pro
pip install -r requirements.txt

# Run!
python rotator.py run
```

## 📖 Usage

### Commands Overview

```bash
python rotator.py scrape          # Scrape proxies from all sources
python rotator.py validate        # Validate proxy pool
python rotator.py export          # Export alive proxies
python rotator.py server          # Start rotating proxy server
python rotator.py run             # Full auto pipeline (recommended!)
python rotator.py dashboard       # Show pool statistics
```

### 🔥 Full Auto Pipeline (Recommended)

```bash
# Scrape → Validate → Auto-refresh every 3 minutes
python rotator.py run

# With proxy server on port 8080
python rotator.py run --server

# Custom refresh interval (5 minutes)
python rotator.py run --interval 300

# With export on each cycle
python rotator.py run --export txt --server
```

### 🌐 Scrape Proxies

```bash
# Scrape from all sources
python rotator.py scrape

# Scrape from specific source
python rotator.py scrape --source proxyscrape
python rotator.py scrape --source github_lists
python rotator.py scrape --source geonode
python rotator.py scrape --source web_scraper

# Scrape + Validate + Export
python rotator.py scrape --validate --export txt
python rotator.py scrape --validate --export json
```

### ✅ Validate Proxies

```bash
# Validate with default settings
python rotator.py validate

# Custom timeout and concurrency
python rotator.py validate --timeout 5 --concurrent 200

# Remove dead proxies after validation
python rotator.py validate --remove-dead
```

### 📁 Export Proxies

```bash
# Export to TXT (IP:PORT format)
python rotator.py export --format txt

# Export to CSV (with full details)
python rotator.py export --format csv

# Export to JSON
python rotator.py export --format json

# Filter by country
python rotator.py export --format txt --country US

# Filter by protocol
python rotator.py export --format txt --protocol socks5
```

### 🖥️ Proxy Server

Start a local HTTP proxy server that automatically rotates the upstream proxy for each request:

```bash
# Start with default settings (localhost:8080)
python rotator.py server

# Custom port
python rotator.py server --port 9090

# With specific rotation strategy
python rotator.py server --strategy round_robin

# Without auto-refresh
python rotator.py server --no-auto-refresh
```

Then configure your browser/app to use `http://127.0.0.1:8080` as proxy. Every request will use a different IP!

Check server status: `http://127.0.0.1:8080/__status`

## 🎯 Rotation Strategies

| Strategy | Description |
|----------|-------------|
| `round_robin` | Cycle through proxies in order |
| `random` | Pick a random alive proxy each time |
| `smart` | Weighted selection based on speed + reliability (default) |
| `fastest` | Always use the fastest available proxy |

## 📡 Proxy Sources (30+ Endpoints)

| Source | Protocols |
|--------|-----------|
| ProxyScrape API | HTTP, SOCKS4, SOCKS5 |
| TheSpeedX/PROXY-List | HTTP, SOCKS4, SOCKS5 |
| monosans/proxy-list | HTTP, SOCKS4, SOCKS5 |
| ShiftyTR/Proxy-List | HTTP, HTTPS, SOCKS4, SOCKS5 |
| clarketm/proxy-list | HTTP |
| hookzof/socks5_list | SOCKS5 |
| MuRongPIG/Proxy-Master | HTTP, SOCKS4, SOCKS5 |
| Zaeem20/FREE_PROXY_LIST | HTTP, HTTPS, SOCKS4, SOCKS5 |
| roosterkid/openproxylist | HTTPS, SOCKS4, SOCKS5 |
| prxchk/proxy-list | HTTP, SOCKS4, SOCKS5 |
| GeoNode API | HTTP, HTTPS, SOCKS4, SOCKS5 |
| free-proxy-list.net | HTTP, HTTPS |
| proxy-list.download | HTTP, HTTPS, SOCKS4, SOCKS5 |
| And more... | ... |

## ⚙️ Configuration

Edit `config.json` to customize:

```json
{
  "validation": {
    "timeout": 10,
    "max_concurrent": 100,
    "retry_count": 2
  },
  "rotation": {
    "strategy": "smart",
    "max_fail_count": 3,
    "auto_refresh_interval": 180
  },
  "server": {
    "host": "127.0.0.1",
    "port": 8080
  }
}
```

| Setting | Description | Default |
|---------|-------------|---------|
| `validation.timeout` | Seconds to wait for proxy response | 10 |
| `validation.max_concurrent` | Simultaneous validation checks | 100 |
| `validation.retry_count` | Retries before marking dead | 2 |
| `rotation.strategy` | Rotation strategy | smart |
| `rotation.max_fail_count` | Fails before removing proxy | 3 |
| `rotation.auto_refresh_interval` | Seconds between auto-refresh | 180 (3 min) |
| `server.host` | Proxy server bind address | 127.0.0.1 |
| `server.port` | Proxy server port | 8080 |

## 📋 Requirements

- Python 3.8+
- Dependencies: `aiohttp`, `aiohttp-socks`, `beautifulsoup4`, `rich`, `requests`

## 📄 License

MIT License — feel free to use, modify, and distribute.

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch
3. Commit your changes
4. Open a Pull Request

---

**Made with ❤️ for the proxy community**
