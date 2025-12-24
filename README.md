# ⚡ UltraQC

<p align="center">
  <img src="ultraqc/static/img/UltraQC_logo.svg" alt="UltraQC Logo" width="400">
</p>

<p align="center">
  <strong>Modern MultiQC Data Aggregation Platform</strong>
</p>

<p align="center">
  <a href="https://github.com/daylily-informatics/UltraQC/actions"><img src="https://github.com/daylily-informatics/UltraQC/workflows/CI/badge.svg" alt="CI Status"></a>
  <a href="https://pypi.org/project/ultraqc/"><img src="https://img.shields.io/pypi/v/ultraqc?color=00d4aa" alt="PyPI"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.9%2B-00d4aa" alt="Python"></a>
  <a href="https://github.com/daylily-informatics/UltraQC/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-GPLv3-00d4aa" alt="License"></a>
</p>

---

## 🚀 Overview

UltraQC is a modern, high-performance web application that collects and visualizes data from multiple [MultiQC](https://multiqc.info) reports. Built with **FastAPI**  and **postgres**.

### ✨ Features

- 🔥 **FastAPI Backend** - Async, high-performance API
- 🎨 **Modern Dark Theme** - Sci-fi neon aesthetics
- 📊 **Interactive Visualizations** - Plotly-powered charts
- 🔐 **JWT Authentication** - Secure token-based auth
- 📈 **Trend Analysis** - Track metrics over time
- 🔄 **Real-time Updates** - WebSocket support
- 🐳 **Docker Ready** - Easy deployment

---

## 📦 Installation

### Quick Install (pip)

```bash
#NOT YET pip install ultraqc
```

### Development Install

```bash
# Clone the repository
git clone https://github.com/daylily-informatics/UltraQC.git
cd UltraQC

# Create virtual environment
python3.10 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install with development dependencies
pip install -e ".[dev]"

# Initialize the database
ultraqc initdb

# Run the development server
ultraqc run
```

### Docker

```bash
docker pull daylily/ultraqc:latest
docker run -p 8000:8000 daylily/ultraqc:latest
```

---

## 🎮 Quick Start

### 1. Start the Server

```bash
# Development mode
ultraqc run --reload

# Production mode
uvicorn ultraqc.app:create_app --factory --host 0.0.0.0 --port 8000
```

### 2. Configure MultiQC

Add to your `~/.multiqc_config.yaml`:

```yaml
ultraqc_url: http://localhost:8000
ultraqc_access_token: YOUR_ACCESS_TOKEN
```

### 3. Upload Reports

```bash
# Direct upload
ultraqc upload /path/to/multiqc_data.json

# Or via MultiQC (after configuration)
multiqc . --ultraqc
```

---

## ⚙️ Configuration

UltraQC uses environment variables for configuration:

| Variable | Default | Description |
|----------|---------|-------------|
| `ULTRAQC_SECRET` | *required* | Secret key for JWT tokens |
| `ULTRAQC_DATABASE_URL` | `sqlite:///ultraqc.db` | Database connection URL |
| `ULTRAQC_DEBUG` | `false` | Enable debug mode |
| `ULTRAQC_HOST` | `0.0.0.0` | Server host |
| `ULTRAQC_PORT` | `8000` | Server port |

Create a `.env` file in your project root:

```env
ULTRAQC_SECRET=your-super-secret-key
ULTRAQC_DATABASE_URL=postgresql://user:pass@localhost/ultraqc
ULTRAQC_DEBUG=false
```

---

## 🐳 Docker Deployment

```yaml
# docker-compose.yml
version: '3.8'
services:
  ultraqc:
    image: daylily/ultraqc:latest
    ports:
      - "8000:8000"
    environment:
      - ULTRAQC_SECRET=your-secret-key
      - ULTRAQC_DATABASE_URL=postgresql://postgres:postgres@db/ultraqc
    depends_on:
      - db
  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=ultraqc
      - POSTGRES_PASSWORD=postgres
    volumes:
      - pgdata:/var/lib/postgresql/data
volumes:
  pgdata:
```

---

## 📚 API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 🤝 Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md).

## 📄 License

GPLv3 - See [LICENSE](LICENSE) for details.

## 🙏 Credits

UltraQC is a modernized fork of [MegaQC](https://github.com/MultiQC/MegaQC), originally created by Phil Ewels and team at SciLifeLab Sweden.

