# Contributing to telegram-protected-media-forwarder

First off, thank you for taking the time to contribute! Contributions from the community make open-source projects great.

---

## Code of Conduct

Please follow standard coding and communication ethics, maintaining a respectful and inclusive environment.

---

## Development Setup

1. **Fork and Clone** the repository.
2. **Setup virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. **Install dependencies** including development tools:
   ```bash
   pip install -r requirements.txt
   pip install -e .[dev]
   ```

---

## Formatting and Linting

We enforce strict linting and formatting rules to keep the codebase clean. Please run the following tools before submitting a Pull Request:

### 1. Code Formatting (Black)
Format Python files to comply with PEP 8:
```bash
black --line-length 100 config/ services/ telegram/ utils/ tests/ main.py setup_wizard.py
```

### 2. Import Sorting (isort)
Ensure imports are organized:
```bash
isort config/ services/ telegram/ utils/ tests/ main.py setup_wizard.py
```

### 3. Static Analysis (Ruff)
Lint your changes:
```bash
ruff check .
```

---

## Testing

Always run tests before pushing to GitHub to ensure you haven't introduced regressions.

To run the test suite:
```bash
pytest tests/
```

Ensure all tests pass. If you add new utility helpers or features, write corresponding unit tests under the `tests/` directory.

---

## Pull Request Guidelines

1. **Create a branch** for your work: `git checkout -b feature/my-new-feature` or `git checkout -b bugfix/issue-description`.
2. Keep commits atomic and write descriptive commit messages.
3. Ensure the code linting and test execution pass locally.
4. Open a Pull Request referencing the issue you are addressing.
