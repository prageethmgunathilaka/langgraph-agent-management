# FastGraph

![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)
![Tests](https://img.shields.io/badge/tests-5%20passed-brightgreen.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

A minimal, production-ready FastAPI microservice skeleton with hello world endpoint.

## Features

- ⚡ **FastAPI** - Modern, fast web framework for building APIs
- 📋 **Auto Documentation** - Interactive API docs at `/docs` and `/redoc`
- 🧪 **Testing** - Comprehensive test suite with pytest
- 🔧 **Code Quality** - Black, isort, flake8 for formatting and linting
- 🏥 **Health Check** - Built-in health endpoint

## Quick Start

### Prerequisites

- Python 3.9+
- pip

### Installation

1. **Clone and navigate:**
   ```bash
   git clone https://github.com/prageethmgunathilaka/fastgraph.git
   cd fastgraph
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -e ".[dev]"
   ```

### Running the Service

**Development server:**
```bash
uvicorn src.main:app --reload
```

**Access the API:**
- API: http://localhost:8000
- Interactive docs: http://localhost:8000/docs
- Alternative docs: http://localhost:8000/redoc
- Health check: http://localhost:8000/health

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET    | `/`      | Hello World |
| GET    | `/health`| Health Check |

## Development

### Testing

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_main.py
```

### Code Quality

```bash
# Format code
black src tests

# Sort imports
isort src tests

# Lint code
flake8 src tests
```

### Project Structure

```
fastgraph/
├── src/
│   ├── __init__.py
│   └── main.py              # FastAPI application
├── tests/
│   ├── __init__.py
│   └── test_main.py         # Test suite
├── pyproject.toml           # Project configuration
└── README.md
```

## Extending the Skeleton

This skeleton provides a solid foundation. To extend it:

1. **Add new endpoints** in `src/main.py` or create separate router modules
2. **Add data models** using Pydantic for request/response validation
3. **Add middleware** for CORS, authentication, logging, etc.
4. **Add database integration** with SQLAlchemy or similar
5. **Add configuration management** with environment variables

## Example Response

```json
{
  "message": "Hello, World!",
  "service": "FastGraph"
}
``` 