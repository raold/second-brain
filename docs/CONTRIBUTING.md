# Contributing to LLM Output Processor

Thanks for your interest in contributing! 🎉

We welcome contributions of all kinds — bug fixes, new features, documentation, and tests.

## Quick Start

1. **Fork the repository** and clone your fork locally:
git clone https://github.com/yourusername/second-brain.git
cd second-brain

2. **Set up the environment**:
make install
make dev

3. **Run tests locally** before submitting:
make test

4. **Lint your code**:
make lint

5. **Commit using conventional commits**:
feat: add new endpoint for async search
fix: resolve circular import in logger
docs: update README for local dev instructions

6. **Push to your fork** and **open a Pull Request** against `main`.

---

## Contribution Guidelines

- Follow **PEP8** and use **Ruff** for linting.
- Ensure **tests** are provided for new features or fixes.
- See [Testing Guide](./TESTING.md) for our approach to mocking OpenAI, Qdrant, Postgres, plugins, and Electron/mobile in integration tests.
- For plugins, Electron/mobile, or new backend modules, include tests and documentation.
- Keep PRs focused and minimal. Large changes? Open an issue first.
- Document your changes where relevant (README, code docstrings, etc.).
- Respect the **Code of Conduct**.

---

## Useful Commands

| Task        | Command       |
|-------------|---------------|
| Install dev dependencies | `make dev` |
| Run tests   | `make test`   |
| Lint code   | `make lint`   |
| Format code | `make format` |

---

## Support & Questions

- For bugs or feature requests, open an [issue](https://github.com/raold/second-brain/issues).
- For discussions, ideas, or help, join our Discord. 
