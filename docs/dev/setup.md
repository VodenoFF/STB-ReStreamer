# Development Setup Guide

This guide will help you set up your development environment for STB-ReStreamer.

## Prerequisites

Before starting, make sure you have the following installed:

- **Python 3.7+** (3.9+ recommended)
- **Git**
- **SQLite 3**
- **pip** (Python package manager)
- A code editor or IDE (Visual Studio Code, PyCharm, etc.)

## Getting the Code

1. **Fork the repository** on GitHub.
2. **Clone your fork** to your local machine:

```bash
git clone https://github.com/your-username/STB-ReStreamer.git
cd STB-ReStreamer
```

3. **Add the upstream repository** as a remote:

```bash
git remote add upstream https://github.com/original-owner/STB-ReStreamer.git
```

## Setting Up a Virtual Environment

It's recommended to use a virtual environment to isolate dependencies:

### Using venv (Python's built-in virtual environment)

```bash
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### Using conda (alternative)

```bash
# Create a conda environment
conda create -n stb-restreamer python=3.9
conda activate stb-restreamer
```

## Installing Dependencies

Install all required dependencies:

```bash
# Update pip
pip install --upgrade pip

# Install development dependencies
pip install -r requirements-dev.txt
```

If `requirements-dev.txt` doesn't exist, install the regular dependencies and common development tools:

```bash
pip install -r requirements.txt
pip install pytest pytest-cov black flake8 mypy isort
```

## Configuration

1. **Create a local configuration file**:

```bash
cp config/default.json config/development.json
```

2. **Edit the configuration** to match your development environment:

```json
{
  "server": {
    "host": "127.0.0.1",
    "port": 8001,
    "debug": true
  },
  "database": {
    "path": "data/dev.db"
  },
  "logging": {
    "level": "DEBUG",
    "file": "logs/dev.log"
  }
}
```

## Database Setup

The application uses SQLite, which will be created automatically when you run the application. However, you can initialize it manually:

```bash
# Create data directory if it doesn't exist
mkdir -p data

# Initialize the database
python -m scripts.init_db
```

## Running the Application

Start the development server:

```bash
python app_new.py
```

The application will be available at `http://localhost:8001`.

## Development Tools

### Code Formatting

Format your code using Black and isort:

```bash
# Format Python code
black .

# Sort imports
isort .
```

### Linting

Lint your code using flake8:

```bash
flake8
```

### Type Checking

Run type checking with mypy:

```bash
mypy .
```

### Running Tests

Run the test suite:

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=src

# Run a specific test file
pytest tests/test_filename.py

# Run a specific test
pytest tests/test_filename.py::test_function_name
```

## Development Workflow

1. **Sync with upstream** to get the latest changes:

```bash
git fetch upstream
git checkout main
git merge upstream/main
```

2. **Create a new branch** for your work:

```bash
git checkout -b feature/your-feature-name
```

3. **Make your changes** and commit them:

```bash
git add .
git commit -m "feat: add your feature"
```

4. **Push your changes** to your fork:

```bash
git push origin feature/your-feature-name
```

5. **Create a pull request** from your fork to the upstream repository.

## Debugging

### Using Visual Studio Code

1. Create a `.vscode/launch.json` file:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Flask",
      "type": "python",
      "request": "launch",
      "module": "flask",
      "env": {
        "FLASK_APP": "app_new.py",
        "FLASK_ENV": "development",
        "FLASK_DEBUG": "1"
      },
      "args": [
        "run",
        "--no-debugger",
        "--host=127.0.0.1",
        "--port=8001"
      ],
      "jinja": true
    },
    {
      "name": "Python: Current File",
      "type": "python",
      "request": "launch",
      "program": "${file}",
      "console": "integratedTerminal"
    }
  ]
}
```

2. Start debugging by pressing F5 or selecting the debug configuration.

### Using PyCharm

1. Go to **Run → Edit Configurations**.
2. Click the **+** button and select **Python**.
3. Set the script path to `app_new.py`.
4. Click **OK** to save.
5. Start debugging by clicking the debug button.

### Debugging with Flask

Enable Flask's debug mode in the configuration or when running:

```bash
# Set environment variable
export FLASK_DEBUG=1  # On Windows: set FLASK_DEBUG=1

# Run with debug mode
python app_new.py --debug
```

## Common Development Tasks

### Adding a New Dependency

When adding a new dependency:

1. Add it to `requirements.txt` with a pinned version.
2. Document why the dependency is needed in a comment.
3. Update the development environment:

```bash
pip install -r requirements.txt
```

### Adding a New Portal Provider

To add a new portal provider:

1. Create a new file in `src/providers/` (e.g., `new_provider.py`).
2. Implement the provider interface (see other providers for examples).
3. Register the provider in `src/providers/__init__.py`.
4. Add tests in `tests/providers/`.
5. Update documentation.

### Working with the Database

To work with the database directly:

```bash
# Open the SQLite database
sqlite3 data/dev.db

# Execute SQL commands
sqlite> .tables
sqlite> SELECT * FROM portals;
sqlite> .quit
```

### Generating Documentation

To generate documentation for the project:

```bash
# Install documentation tools
pip install sphinx sphinx-rtd-theme

# Generate API documentation
sphinx-apidoc -o docs/api src/

# Build HTML documentation
cd docs
make html
```

## Getting Help

If you need help with development:

- Check the [Architecture Overview](architecture.md) for system design
- Review existing code for examples
- Ask questions in the community channels
- Open an issue for bigger problems

## Troubleshooting

### Common Issues

#### "Module not found" errors

Ensure your virtual environment is activated and all dependencies are installed.

#### Database errors

Check file permissions and that the data directory exists.

#### Port already in use

Change the port in the configuration if 8001 is already in use.

#### Changes not reflecting in the browser

Clear your browser cache or use incognito/private browsing.

## Additional Resources

- [Flask Documentation](https://flask.palletsprojects.com/)
- [SQLite Documentation](https://www.sqlite.org/docs.html)
- [Python Testing with pytest](https://docs.pytest.org/) 