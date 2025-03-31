# Contributing to STB-ReStreamer

Thank you for your interest in contributing to STB-ReStreamer! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Branching Strategy](#branching-strategy)
- [Commit Guidelines](#commit-guidelines)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Documentation](#documentation)
- [Issue Reporting](#issue-reporting)
- [Feature Requests](#feature-requests)
- [Community](#community)

## Code of Conduct

All contributors are expected to adhere to the project's Code of Conduct. Please read [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) before contributing.

## Getting Started

1. **Fork the repository** on GitHub.
2. **Clone your fork** to your local machine.
3. **Set up the development environment** by following the instructions in [setup.md](setup.md).
4. **Create a new branch** for your changes.
5. **Make your changes** and commit them with clear messages.
6. **Push your branch** to your fork on GitHub.
7. **Submit a pull request** from your branch to the main repository.

## Development Workflow

1. **Check the issue tracker** for open issues that need attention.
2. **Comment on an issue** to indicate you're working on it.
3. **Create a new branch** for your work.
4. **Implement your changes** following the coding standards.
5. **Write tests** for your changes.
6. **Update documentation** to reflect your changes.
7. **Submit a pull request** for review.

## Branching Strategy

We follow a simplified Git workflow:

- `main` - Stable branch reflecting the production code
- `dev` - Development branch for integrating features
- `feature/*` - Feature branches for new features or enhancements
- `bugfix/*` - Bugfix branches for bug fixes
- `hotfix/*` - Hotfix branches for critical production fixes

Example branch names:
- `feature/add-xtream-provider`
- `bugfix/fix-stream-timeout`
- `hotfix/security-vulnerability-fix`

## Commit Guidelines

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification for commit messages:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

Types include:
- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring without functionality changes
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

Examples:
```
feat(portal): add support for XC Updates protocol
fix(streaming): resolve issue with stream timeout
docs(api): update WebSocket API documentation
```

## Pull Request Process

1. **Update your fork** with the latest changes from the upstream repository.
2. **Create a new branch** with a descriptive name.
3. **Implement your changes** with appropriate tests and documentation.
4. **Run all tests** to ensure they pass.
5. **Submit a pull request** with a clear description of the changes.
6. **Address any feedback** from code reviews.
7. **Update your pull request** if needed.

### Pull Request Template

When creating a pull request, please include:

- **Description** of the changes
- **Issue number(s)** being addressed
- **Type of change** (bugfix, feature, documentation, etc.)
- **Testing performed**
- **Screenshots** (if applicable)
- **Checklist** of completed items

## Coding Standards

We follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) for Python code with some modifications:

### Python Guidelines

- Use **4 spaces** for indentation (no tabs)
- Maximum line length of **88 characters** (following Black defaults)
- Use **docstrings** for all public modules, functions, classes, and methods
- Use **type hints** for function parameters and return values
- Use **snake_case** for functions and variables
- Use **PascalCase** for classes
- Use **UPPERCASE** for constants

### Code Formatting

We use the following tools for code formatting and linting:

- **[Black](https://black.readthedocs.io/)** for code formatting
- **[isort](https://pycqa.github.io/isort/)** for import sorting
- **[flake8](https://flake8.pycqa.org/)** for linting
- **[mypy](http://mypy-lang.org/)** for static type checking

You can run these tools before committing:

```bash
# Format code
black .

# Sort imports
isort .

# Run linters
flake8
mypy .
```

## Testing

All code changes should include appropriate tests:

### Test Guidelines

- Write **unit tests** for individual functions and methods
- Write **integration tests** for component interactions
- Write **functional tests** for user-facing features
- Aim for high **test coverage**
- Run all tests before submitting a pull request

### Running Tests

To run the test suite:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run a specific test file
pytest tests/test_portal_manager.py
```

## Documentation

Documentation is a crucial part of the project:

### Documentation Guidelines

- Update **docstrings** for any modified code
- Update **README.md** if needed
- Update **user documentation** for user-facing changes
- Update **API documentation** for API changes
- Write **clear commit messages**
- Include **comments** for complex code sections

## Issue Reporting

When reporting issues, please include:

- A **clear description** of the issue
- **Steps to reproduce** the problem
- **Expected behavior**
- **Actual behavior**
- **Screenshots** if applicable
- **Environment information**:
  - STB-ReStreamer version
  - Operating system
  - Python version
  - Browser (for UI issues)

## Feature Requests

For feature requests, please include:

- A **clear description** of the feature
- The **motivation** for adding this feature
- Any **alternative solutions** you've considered
- Any **reference implementations** or examples

## Community

Join our community channels for discussions:

- **GitHub Discussions**: For long-form conversations and questions
- **Issue Tracker**: For bugs and feature requests
- **Discord**: For real-time chat and collaboration

## License

By contributing to STB-ReStreamer, you agree that your contributions will be licensed under the project's license. See [LICENSE](LICENSE) for details. 