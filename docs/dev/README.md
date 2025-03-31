# STB-ReStreamer Developer Documentation

Welcome to the STB-ReStreamer developer documentation. This section provides information for developers who want to understand, contribute to, or extend the STB-ReStreamer project.

## Table of Contents

### Getting Started
- [Development Setup](setup.md) - Set up your development environment
- [Architecture Overview](architecture.md) - Understand the system architecture
- [Contributing Guidelines](contributing.md) - Learn how to contribute to the project

### Code Organization
- [Project Structure](project-structure.md) - Overview of the codebase organization
- [Core Components](core-components.md) - Detailed documentation of core components
- [Service Layer](services.md) - Documentation of service layer components
- [API Design](api-design.md) - Overview of the API design

### Implementation Details
- [Portal Providers](providers.md) - Implementation of different portal providers
- [Streaming Protocol](streaming.md) - Streaming implementation details
- [Database Schema](database-schema.md) - Database tables and relationships
- [Authentication](authentication.md) - Authentication implementation
- [WebSocket Implementation](websocket.md) - Real-time updates implementation

### Development Guides
- [Adding a New Portal Provider](guides/new-provider.md) - How to implement a new portal provider
- [Adding a New Feature](guides/new-feature.md) - Guide for implementing new features
- [UI Development](guides/ui-development.md) - Frontend development guidelines
- [API Extension](guides/api-extension.md) - Extending the API

### Testing
- [Testing Strategy](testing/index.md) - Overall testing approach and framework
- [Unit Testing](testing/unit-testing.md) - Writing unit tests for individual components
- [Integration Testing](testing/integration-testing.md) - Testing component interactions
- [Test Fixtures](testing/fixtures.md) - Using and creating test fixtures

The project uses pytest as its testing framework. The test suite is organized into:

- **Unit tests** (`tests/unit/`): Test individual components in isolation
- **Integration tests** (`tests/integration/`): Test interactions between components

To run tests, install the development dependencies with `pip install -r requirements-dev.txt` 
and then run `python run_tests.py` or simply `pytest`.

### Deployment
- [Production Deployment](deployment/production.md) - Best practices for production deployments
- [Docker Deployment](deployment/docker.md) - Using Docker for containerized deployment
- [Systemd Configuration](deployment/systemd.md) - Running as a systemd service on Linux
- [HTTPS Configuration](deployment/https.md) - Setting up secure HTTPS access
- [Installation Script](deployment/installation.md) - Automated installation options

STB-ReStreamer can be deployed in several ways depending on your needs:
- As a systemd service for traditional Linux deployments
- As a Docker container for easier management and isolation
- With HTTPS support through reverse proxies like Nginx or Caddy
- Using the automated installation script for quick setup

Choose the deployment method that best suits your environment and requirements.

### Best Practices
- [Code Style Guide](best-practices/code-style.md) - Coding style guidelines
- [Performance Optimization](best-practices/performance.md) - Performance best practices
- [Security Guidelines](best-practices/security.md) - Security best practices

## Contributing to Documentation

The developer documentation is a work in progress. If you find missing or outdated information, please consider contributing improvements. See the [Contributing Guidelines](contributing.md) for details on how to contribute.

## Future Documentation

The following documents are planned for future development:

- Complete API reference
- Frontend architecture
- Monitoring and logging
- Scaling strategies
- Mobile compatibility
- Performance benchmarks

## Getting Help

If you need help with development:

- Ask questions in the community channels
- Review existing code for examples
- Open an issue for technical questions
- Refer to the [user documentation](/docs/user/) for feature information 