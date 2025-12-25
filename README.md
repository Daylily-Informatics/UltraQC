# ⚡ UltraQC

<p align="center">
  <img src="ultraqc/static/img/UltraQC_logo.svg" alt="UltraQC Logo" width="400">
</p>

<p align="center">
  <strong>Modern QC Data Aggregation Platform</strong>
</p>

<p align="center">
  <a href="https://github.com/Daylily-Informatics/UltraQC/actions"><img src="https://github.com/Daylily-Informatics/UltraQC/workflows/CI/badge.svg" alt="CI Status"></a>
  <a href="https://pypi.org/project/ultraqc/"><img src="https://img.shields.io/pypi/v/ultraqc?color=00d4aa" alt="PyPI"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.9%2B-00d4aa" alt="Python"></a>
  <a href="https://github.com/Daylily-Informatics/UltraQC/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-GPLv3-00d4aa" alt="License"></a>
</p>

---

## 🚀 Overview

UltraQC is a modern, high-performance web application that collects and visualizes QC data from multiple sources, including [MultiQC](https://multiqc.info) reports and custom data pipelines. Built with **FastAPI** and featuring a sleek sci-fi neon dark theme.

### ✨ Features

- 🔥 **FastAPI Backend** - Async, high-performance Python API
- 🎨 **Modern Dark Theme** - Sci-fi neon aesthetics
- 📊 **Interactive Visualizations** - Plotly-powered charts
- 🔐 **JWT Authentication** - Secure token-based auth
- 📈 **Trend Analysis** - Track metrics over time across runs
- � **Flexible Data Input** - Accept data from MultiQC or any custom source
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
git clone https://github.com/Daylily-Informatics/UltraQC.git
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

### 2. Register & Get API Token

1. Open http://localhost:8000 in your browser
2. Register a new account (first user becomes admin)
3. Go to your profile to get your API access token

### 3. Configure MultiQC (Optional)

If using MultiQC, add to your `~/.multiqc_config.yaml`:

```yaml
ultraqc_url: http://localhost:8000
ultraqc_access_token: YOUR_ACCESS_TOKEN
```

### 4. Upload Reports

```bash
# Direct upload via CLI
ultraqc upload /path/to/multiqc_data.json

# Or via MultiQC (after configuration)
multiqc . --ultraqc
```

---

## 🔌 Sending Data from Non-MultiQC Sources

UltraQC can accept QC data from **any source**, not just MultiQC. This allows you to integrate custom pipelines, other QC tools, or even manual data entry.

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/upload_data` | POST | Queue raw JSON data for processing |
| `/rest_api/v1/uploads` | POST | Upload a JSON file directly |

### Required JSON Format

Data must follow this structure (compatible with MultiQC's `multiqc_data.json`):

```json
{
  "config_creation_date": "2024-01-15, 14:30",
  "config_title": "My QC Report",

  "report_saved_raw_data": {
    "multiqc_general_stats": {
      "sample_001": {
        "percent_gc": 45.2,
        "total_sequences": 1000000,
        "avg_sequence_length": 150
      },
      "sample_002": {
        "percent_gc": 48.1,
        "total_sequences": 1200000,
        "avg_sequence_length": 150
      }
    },
    "multiqc_custom_tool": {
      "sample_001": {
        "custom_metric_1": 0.95,
        "custom_metric_2": 123.4
      }
    }
  },

  "report_general_stats_data": [
    {
      "sample_001": {"percent_gc": 45.2, "total_sequences": 1000000},
      "sample_002": {"percent_gc": 48.1, "total_sequences": 1200000}
    }
  ]
}
```

### Key Fields

| Field | Required | Description |
|-------|----------|-------------|
| `report_saved_raw_data` | **Yes** | Main data container with sections and samples |
| `config_creation_date` | No | Report timestamp (format: `YYYY-MM-DD, HH:MM`) |
| `config_title` | No | Human-readable report title |
| `report_general_stats_data` | No | Summary statistics for quick display |

### Data Structure

```
report_saved_raw_data/
├── multiqc_{section_name}/     # Section names (prefix with multiqc_)
│   ├── {sample_name}/          # Sample identifier
│   │   ├── {metric_key}: value # Metric name and value
│   │   └── ...
│   └── ...
└── ...
```

### Example: Sending Custom QC Data

**Using curl:**

```bash
curl -X POST http://localhost:8000/api/upload_data \
  -H "Content-Type: application/json" \
  -H "access_token: YOUR_TOKEN" \
  -d '{
    "config_creation_date": "2024-01-15, 14:30",
    "report_saved_raw_data": {
      "multiqc_my_pipeline": {
        "sample_A": {"quality_score": 0.95, "read_count": 50000},
        "sample_B": {"quality_score": 0.87, "read_count": 45000}
      }
    }
  }'
```

**Using Python:**

```python
import requests

data = {
    "config_creation_date": "2024-01-15, 14:30",
    "report_saved_raw_data": {
        "multiqc_alignment": {
            "sample_001": {
                "mapped_reads": 950000,
                "mapping_rate": 0.95,
                "duplicate_rate": 0.12
            }
        }
    }
}

response = requests.post(
    "http://localhost:8000/api/upload_data",
    json=data,
    headers={"access_token": "YOUR_TOKEN"}
)
print(response.json())
```

### ⚠️ Current Limitations (Work Needed)

The current implementation has some limitations for non-MultiQC data:

1. **Section naming**: Sections must be prefixed with `multiqc_` (e.g., `multiqc_my_tool`)
2. **Plot data**: The `report_plot_data` structure is MultiQC-specific; custom visualizations require the full MultiQC plot format
3. **Schema validation**: No JSON schema validation on upload - malformed data may cause errors during processing
4. **Metric types**: All values are stored as strings; numeric aggregation assumes float conversion

**Potential Improvements:**
- Add a simplified `/api/v2/submit` endpoint that accepts a cleaner format
- Add JSON schema validation with helpful error messages
- Support direct metric submission without the `multiqc_` prefix requirement
- Add a web UI for manual data entry

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

UltraQC is a modernized fork of [MegaQC](https://github.com/MultiQC/MegaQC), originally created by Phil Ewels and team at SciLifeLab Sweden. Now maintained by [Daylily Informatics](https://github.com/Daylily-Informatics).

