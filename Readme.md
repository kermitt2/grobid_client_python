# GROBID Client Python

[![PyPI version](https://badge.fury.io/py/grobid_client_python.svg)](https://badge.fury.io/py/grobid_client_python)
[![SWH](https://archive.softwareheritage.org/badge/origin/https://github.com/kermitt2/grobid_client_python/)](https://archive.softwareheritage.org/browse/origin/https://github.com/kermitt2/grobid_client_python/)
[![License](http://img.shields.io/:license-apache-blue.svg)](http://www.apache.org/licenses/LICENSE-2.0.html)

A simple, efficient Python client for [GROBID](https://github.com/kermitt2/grobid) REST services that provides concurrent processing capabilities for PDF documents, reference strings, and patents.

## 📋 Table of Contents

- [Features](#-features)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [Usage](#-usage)
  - [Command Line Interface](#command-line-interface)
  - [Python Library](#python-library)
- [Configuration](#-configuration)
- [Services](#-services)
- [Testing](#-testing)
- [Performance](#-performance)
- [Development](#-development)
- [License](#-license)

## ✨ Features

- **Concurrent Processing**: Efficiently process multiple documents in parallel
- **Flexible Input**: Process PDF files, text files with references, and XML patents
- **Configurable**: Customizable server settings, timeouts, and processing options
- **Command Line & Library**: Use as a standalone CLI tool or import into your Python projects
- **Coordinate Extraction**: Optional PDF coordinate extraction for precise element positioning
- **Sentence Segmentation**: Layout-aware sentence segmentation capabilities

## 📋 Prerequisites

- **Python**: 3.8 - 3.13 (tested versions)
- **GROBID Server**: A running GROBID service instance
  - Local installation: [GROBID Documentation](http://grobid.readthedocs.io/)
  - Docker: `docker run -t --rm -p 8070:8070 lfoppiano/grobid:0.8.2`
  - Default server: `http://localhost:8070`
  - Online demo: https://lfoppiano-grobid.hf.space (usage limits apply), more details [here](https://grobid.readthedocs.io/en/latest/getting_started/#using-grobid-from-the-cloud).

> [!IMPORTANT]
> GROBID supports Windows only through Docker containers. See the [Docker documentation](https://grobid.readthedocs.io/en/latest/Grobid-docker/) for details.

## 🚀 Installation

Choose one of the following installation methods:

### PyPI (Recommended)
```bash
pip install grobid-client-python
```

### Development Version
```bash
pip install git+https://github.com/kermitt2/grobid_client_python.git
```

### Local Development
```bash
git clone https://github.com/kermitt2/grobid_client_python
cd grobid_client_python
pip install -e .
```

## ⚡ Quick Start

### Command Line
```bash
# Process PDFs in a directory
grobid_client --input ./pdfs --output ./output processFulltextDocument

# Process with custom server
grobid_client --server https://your-grobid-server.com --input ./pdfs processFulltextDocument
```

### Python Library
```python
from grobid_client.grobid_client import GrobidClient

# Create client instance
client = GrobidClient(config_path="./config.json")

# Process documents
client.process("processFulltextDocument", "/path/to/pdfs", n=10)
```

## 📖 Usage

### Command Line Interface

The client provides a comprehensive CLI with the following syntax:

```bash
grobid_client [OPTIONS] SERVICE
```

#### Available Services

| Service                     | Description                       | Input Format                       |
|-----------------------------|-----------------------------------|------------------------------------|
| `processFulltextDocument`   | Extract full document structure   | PDF files                          |
| `processHeaderDocument`     | Extract document metadata         | PDF files                          |
| `processReferences`         | Extract bibliographic references  | PDF files                          |
| `processCitationList`       | Parse citation strings            | Text files (one citation per line) |
| `processCitationPatentST36` | Process patent citations          | XML ST36 format                    |
| `processCitationPatentPDF`  | Process patent PDFs               | PDF files                          |

#### Common Options

| Option      | Description              | Default                 |
|-------------|--------------------------|-------------------------|
| `--input`   | Input directory path     | Required                |
| `--output`  | Output directory path    | Same as input           |
| `--server`  | GROBID server URL        | `http://localhost:8070` |
| `--n`       | Concurrency level        | 10                      |
| `--config`  | Config file path         | Optional                |
| `--force`   | Overwrite existing files | False                   |
| `--verbose` | Enable verbose logging   | False                   |

#### Processing Options

| Option                       | Description                               |
|------------------------------|-------------------------------------------|
| `--generateIDs`              | Generate random XML IDs                   |
| `--consolidate_header`       | Consolidate header metadata               |
| `--consolidate_citations`    | Consolidate bibliographic references      |
| `--include_raw_citations`    | Include raw citation text                 |
| `--include_raw_affiliations` | Include raw affiliation text              |
| `--teiCoordinates`           | Add PDF coordinates to XML                |
| `--segmentSentences`         | Segment sentences with coordinates        |
| `--flavor`                   | Processing flavor for fulltext extraction |

#### Examples

```bash
# Basic fulltext processing
grobid_client --input ~/documents --output ~/results processFulltextDocument

# High concurrency with coordinates
grobid_client --input ~/pdfs --output ~/tei --n 20 --teiCoordinates processFulltextDocument

# Process citations with custom server
grobid_client --server https://grobid.example.com --input ~/citations.txt processCitationList

# Force reprocessing with sentence segmentation
grobid_client --input ~/docs --force --segmentSentences processFulltextDocument
```

### Python Library

#### Basic Usage

```python
from grobid_client.grobid_client import GrobidClient

# Initialize with default localhost server
client = GrobidClient()

# Initialize with custom server
client = GrobidClient(grobid_server="https://your-server.com")

# Initialize with config file
client = GrobidClient(config_path="./config.json")

# Process documents
client.process(
    service="processFulltextDocument",
    input_path="/path/to/pdfs",
    output_path="/path/to/output",
    n=20
)
```

#### Advanced Usage

```python
# Process with specific options
client.process(
    service="processFulltextDocument",
    input_path="/path/to/pdfs",
    output_path="/path/to/output",
    n=10,
    generateIDs=True,
    consolidate_header=True,
    teiCoordinates=True,
    segmentSentences=True
)

# Process citation lists
client.process(
    service="processCitationList",
    input_path="/path/to/citations.txt",
    output_path="/path/to/output"
)
```

## ⚙️ Configuration

Configuration can be provided via a JSON file. When using the CLI, the `--server` argument overrides the config file settings.

### Default Configuration

```json
{
    "grobid_server": "http://localhost:8070",
    "batch_size": 1000,
    "sleep_time": 5,
    "timeout": 60,
    "coordinates": ["persName", "figure", "ref", "biblStruct", "formula", "s"]
}
```

### Configuration Parameters

| Parameter       | Description                                                                                                      | Default                 |
|-----------------|------------------------------------------------------------------------------------------------------------------|-------------------------|
| `grobid_server` | GROBID server URL                                                                                                | `http://localhost:8070` |
| `batch_size`    | Thread pool size. **Tune carefully: a large batch size will result in the data being written less frequently**   | 1000                    |
| `sleep_time`    | Wait time when server is busy (seconds)                                                                          | 5                       |
| `timeout`       | Client-side timeout (seconds)                                                                                    | 180                     |
| `coordinates`   | XML elements for coordinate extraction                                                                           | See above               |

> [!TIP]
> Since version 0.0.12, the config file is optional. The client will use default localhost settings if no configuration is provided.

## 🔬 Services

### Fulltext Document Processing
Extracts complete document structure including headers, body text, figures, tables, and references.

```bash
grobid_client --input pdfs/ --output results/ processFulltextDocument
```

### Header Document Processing
Extracts only document metadata (title, authors, abstract, etc.).

```bash
grobid_client --input pdfs/ --output headers/ processHeaderDocument
```

### Reference Processing
Extracts and structures bibliographic references from documents.

```bash
grobid_client --input pdfs/ --output refs/ processReferences
```

### Citation List Processing
Parses raw citation strings from text files.

```bash
grobid_client --input citations.txt --output parsed/ processCitationList
```

> [!TIP]
> For citation lists, input should be text files with one citation string per line.

## 🧪 Testing

The project includes comprehensive unit and integration tests using pytest.

### Running Tests

```bash
# Install development dependencies
pip install -e .[dev]

# Run all tests
pytest

# Run with coverage
pytest --cov=grobid_client

# Run specific test file
pytest tests/test_client.py

# Run with verbose output
pytest -v
```

### Test Structure

- `tests/test_client.py` - Unit tests for the base API client
- `tests/test_grobid_client.py` - Unit tests for the GROBID client
- `tests/test_integration.py` - Integration tests with real GROBID server
- `tests/conftest.py` - Test configuration and fixtures

### Continuous Integration

Tests are automatically run via GitHub Actions on:
- Push to main branch
- Pull requests
- Multiple Python versions (3.8-3.13)

## 📊 Performance

Benchmark results for processing **136 PDFs** (3,443 pages total, ~25 pages per PDF) on Intel Core i7-4790K CPU 4.00GHz:

| Concurrency | Runtime (s) | s/PDF | PDF/s |
|-------------|-------------|-------|-------|
| 1           | 209.0       | 1.54  | 0.65  |
| 2           | 112.0       | 0.82  | 1.21  |
| 3           | 80.4        | 0.59  | 1.69  |
| 5           | 62.9        | 0.46  | 2.16  |
| 8           | 55.7        | 0.41  | 2.44  |
| 10          | 55.3        | 0.40  | 2.45  |

![Runtime Plot](resources/20180928112135.png)

### Additional Benchmarks

- **Header processing**: 3.74s for 136 PDFs (36 PDF/s) with n=10
- **Reference extraction**: 26.9s for 136 PDFs (5.1 PDF/s) with n=10  
- **Citation parsing**: 4.3s for 3,500 citations (814 citations/s) with n=10

## 🛠️ Development

### Setting Up Development Environment

```bash
# Clone the repository
git clone https://github.com/kermitt2/grobid_client_python
cd grobid_client_python

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode with test dependencies
pip install -e .[dev]

# Install pre-commit hooks (optional)
pre-commit install
```

### Creating a New Release

The project uses `bump-my-version` for version management:

```bash
# Install bump-my-version
pip install bump-my-version

# Bump version (patch, minor, or major)
bump-my-version bump patch

# The release will be automatically published to PyPI
```

### Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Run the test suite (`pytest`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## 📄 License

Distributed under the [Apache 2.0 License](http://www.apache.org/licenses/LICENSE-2.0). See `LICENSE` for more information.

## 👥 Authors & Contact

**Main Author**: Patrice Lopez (patrice.lopez@science-miner.com)  
**Maintainer**: Luca Foppiano (luca@sciencialab.com)

## 🔗 Links

- [GROBID Documentation](https://grobid.readthedocs.io/)
- [PyPI Package](https://pypi.org/project/grobid-client-python/)
- [GitHub Repository](https://github.com/kermitt2/grobid_client_python)
- [Issue Tracker](https://github.com/kermitt2/grobid_client_python/issues)
