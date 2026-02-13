# Poetry Quick Reference Guide

A quick reference for common Poetry commands used in this project.

---

## 📦 Installation

```bash
# Install Poetry (if not already installed)
curl -sSL https://install.python-poetry.org | python3 -

# Verify installation
poetry --version
```

---

## 🚀 Getting Started

```bash
# Install all dependencies (including dev)
poetry install

# Install only production dependencies
poetry install --only main

# Install dependencies without creating virtualenv in project
poetry install --no-root
```

---

## 📚 Managing Dependencies

### Adding Dependencies

```bash
# Add a production dependency
poetry add fastapi

# Add a specific version
poetry add "fastapi>=0.115.0"

# Add a dev dependency
poetry add --group dev pytest

# Add multiple dependencies
poetry add httpx redis pydantic
```

### Removing Dependencies

```bash
# Remove a dependency
poetry remove fastapi

# Remove a dev dependency
poetry remove --group dev pytest
```

### Updating Dependencies

```bash
# Update all dependencies
poetry update

# Update a specific package
poetry update fastapi

# Show outdated packages
poetry show --outdated
```

---

## 🏃 Running Commands

```bash
# Run Python script
poetry run python main.py

# Run uvicorn server
poetry run uvicorn main:app --reload

# Run tests
poetry run pytest

# Run black formatter
poetry run black .

# Run ruff linter
poetry run ruff check .
```

---

## 🔍 Information Commands

```bash
# Show all installed packages
poetry show

# Show details of a specific package
poetry show fastapi

# Show dependency tree
poetry show --tree

# Show only production dependencies
poetry show --only main

# Show only dev dependencies
poetry show --only dev
```

---

## 🌍 Virtual Environment

```bash
# Show virtualenv info
poetry env info

# Show virtualenv path
poetry env info --path

# Activate virtualenv (manual)
source $(poetry env info --path)/bin/activate

# Deactivate virtualenv
deactivate

# Remove virtualenv
poetry env remove python3.13

# List all virtualenvs for this project
poetry env list
```

---

## 🔒 Lock File

```bash
# Generate/update poetry.lock
poetry lock

# Update lock file without upgrading packages
poetry lock --no-update

# Install from lock file
poetry install
```

---

## 🔧 Configuration

```bash
# Show current configuration
poetry config --list

# Set virtualenvs in project directory
poetry config virtualenvs.in-project true

# Disable virtualenv creation
poetry config virtualenvs.create false
```

---

## 📦 Building & Publishing

```bash
# Build package (creates wheel and sdist)
poetry build

# Publish to PyPI
poetry publish

# Build and publish in one command
poetry publish --build
```

---

## 🐛 Debugging

```bash
# Check validity of pyproject.toml
poetry check

# Show dependency tree to debug conflicts
poetry show --tree

# Verbose output for debugging
poetry install -vvv

# Clear cache
poetry cache clear pypi --all
```

---

## 🎯 Common Workflows

### Starting Fresh

```bash
# Clone repo and install dependencies
git clone <repo>
cd yahoo-services
poetry install
```

### Adding a New Package

```bash
# Add package
poetry add httpx

# Verify it was added
poetry show httpx

# Update lock file
poetry lock

# Commit changes
git add pyproject.toml poetry.lock
git commit -m "feat: add httpx dependency"
```

### Updating Dependencies

```bash
# Check for outdated packages
poetry show --outdated

# Update specific package
poetry update fastapi

# Update all packages
poetry update

# Commit changes
git add poetry.lock
git commit -m "chore: update dependencies"
```

### Running Development Server

```bash
# Run with Poetry
poetry run python main.py

# Or activate virtualenv first
source $(poetry env info --path)/bin/activate
python main.py
```

---

## 🔥 Quick Commands for This Project

```bash
# Install dependencies
poetry install --no-root

# Run development server
poetry run python main.py

# Run tests
poetry run pytest

# Format code
poetry run black .

# Lint code
poetry run ruff check .

# Add new dependency
poetry add <package-name>

# Update dependencies
poetry update

# Show installed packages
poetry show
```

---

## 🚨 Troubleshooting

### Issue: "Poetry not found"

```bash
# Add Poetry to PATH
export PATH="$HOME/.local/bin:$PATH"

# Or reinstall Poetry
curl -sSL https://install.python-poetry.org | python3 -
```

### Issue: "Lock file out of sync"

```bash
# Regenerate lock file
poetry lock

# Install from updated lock file
poetry install
```

### Issue: "Virtualenv conflicts"

```bash
# Remove existing virtualenv
poetry env remove python3.13

# Reinstall
poetry install
```

### Issue: "Dependency conflicts"

```bash
# Show dependency tree to identify conflict
poetry show --tree

# Update problematic package
poetry update <package-name>

# Or specify compatible version
poetry add "package-name@^X.Y.Z"
```

---

## 📖 Resources

- [Official Poetry Documentation](https://python-poetry.org/docs/)
- [Poetry GitHub Repository](https://github.com/python-poetry/poetry)
- [Poetry Commands Reference](https://python-poetry.org/docs/cli/)

---

## 🎯 Best Practices

1. **Always commit both files**: `pyproject.toml` and `poetry.lock`
2. **Use lock file for deployments**: Ensures reproducible builds
3. **Group dependencies**: Use `--group dev` for development dependencies
4. **Specify version constraints**: Use `^` for compatible versions
5. **Update regularly**: Run `poetry update` to keep dependencies current
6. **Use Poetry run**: Ensures commands run in correct environment

---

Last Updated: 2026-02-13
