# Git Workflow for Yahoo-Services

## Branching Strategy

This project follows a structured git workflow to maintain code quality and stability.

### Branch Types

```
main
  └── develop
      ├── feature/implement-api-routes
      ├── feature/add-alpha-vantage-fallback
      ├── bugfix/fix-rate-limit-handling
      └── hotfix/critical-production-fix
```

### Branch Descriptions

| Branch Type | Purpose | Base Branch | Merge Target |
|-------------|---------|-------------|--------------|
| `main` | Production-ready code | — | — |
| `develop` | Integration branch | `main` | `main` |
| `feature/<name>` | New features | `develop` | `develop` |
| `bugfix/<name>` | Bug fixes | `develop` | `develop` |
| `hotfix/<name>` | Critical production fixes | `main` | `main` + `develop` |

---

## Rules

### ❌ NEVER Work Directly on Main
**Main branch is protected and contains only production-ready code.**

### ✅ All Work Happens in Feature Branches
All development work must be done in dedicated feature/bugfix/hotfix branches.

---

## Workflow Examples

### 1. Creating a New Feature

```bash
# Start from develop
git checkout develop
git pull origin develop

# Create feature branch
git checkout -b feature/add-global-context-endpoint

# Work on your feature
# ... make changes ...

# Commit your work
git add .
git commit -m "feat: add global context endpoint with caching"

# Push to remote
git push -u origin feature/add-global-context-endpoint

# When ready, merge to develop
git checkout develop
git merge feature/add-global-context-endpoint

# Push develop
git push origin develop

# Clean up feature branch (optional)
git branch -d feature/add-global-context-endpoint
```

### 2. Fixing a Bug

```bash
# Start from develop
git checkout develop
git pull origin develop

# Create bugfix branch
git checkout -b bugfix/fix-rate-limit-error

# Fix the bug
# ... make changes ...

# Commit
git add .
git commit -m "fix: handle Yahoo rate limit errors correctly"

# Merge to develop
git checkout develop
git merge bugfix/fix-rate-limit-error

# Push
git push origin develop
```

### 3. Critical Production Hotfix

```bash
# Start from main (production)
git checkout main
git pull origin main

# Create hotfix branch
git checkout -b hotfix/fix-critical-cache-bug

# Fix the issue
# ... make changes ...

# Commit
git add .
git commit -m "hotfix: fix Redis connection timeout"

# Merge to main
git checkout main
git merge hotfix/fix-critical-cache-bug
git push origin main

# Also merge to develop to keep it in sync
git checkout develop
git merge hotfix/fix-critical-cache-bug
git push origin develop

# Clean up
git branch -d hotfix/fix-critical-cache-bug
```

### 4. Releasing to Production

```bash
# When develop is stable and ready for production
git checkout main
git pull origin main

# Merge develop into main
git merge develop

# Tag the release (optional)
git tag -a v1.0.0 -m "Release v1.0.0: Initial API routes implementation"

# Push to production
git push origin main
git push origin --tags
```

---

## Commit Message Conventions

Follow conventional commits format:

### Format
```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `refactor`: Code refactoring (no functional changes)
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `chore`: Maintenance tasks (dependencies, config, etc.)
- `hotfix`: Critical production fix

### Examples

```bash
# Feature
git commit -m "feat(api): add global context endpoint with S&P 500, NASDAQ, VIX"

# Bug fix
git commit -m "fix(cache): handle Redis connection timeout gracefully"

# Refactor
git commit -m "refactor(services): extract common error handling to base service"

# Documentation
git commit -m "docs: update API endpoints documentation"

# Chore
git commit -m "chore(deps): update yfinance to 0.2.18"

# Hotfix
git commit -m "hotfix(rate-limit): fix Yahoo Finance rate limit handling"
```

---

## Branch Naming Conventions

### Feature Branches
```
feature/add-global-context-endpoint
feature/add-fundamentals-batch-endpoint
feature/implement-alpha-vantage-fallback
feature/add-structured-logging
```

### Bugfix Branches
```
bugfix/fix-rate-limit-error
bugfix/fix-cache-key-collision
bugfix/fix-response-format
```

### Hotfix Branches
```
hotfix/fix-critical-memory-leak
hotfix/fix-redis-connection-timeout
hotfix/fix-yahoo-api-auth-error
```

**Rules:**
- Use lowercase with hyphens (kebab-case)
- Be descriptive but concise
- Start with type prefix (feature/, bugfix/, hotfix/)

---

## Current Branch Status

### Initial Setup (Completed)
- ✅ `main` — Initial project structure, requirements, Cursor rules
- ✅ `develop` — Created from main
- ✅ `feature/implement-api-routes` — **Current working branch**

### Next Steps
1. Complete API routes implementation on `feature/implement-api-routes`
2. Test endpoints thoroughly
3. Merge to `develop`
4. Deploy to staging (from `develop`)
5. When stable, merge `develop` to `main` for production

---

## Useful Commands

### Check Current Branch
```bash
git branch          # List all local branches
git branch -a       # List all branches (local + remote)
git status          # Show current branch and changes
```

### Switch Branches
```bash
git checkout develop                     # Switch to develop
git checkout -b feature/new-feature      # Create and switch to new branch
```

### Update from Remote
```bash
git pull origin develop                  # Pull latest develop
git fetch origin                         # Fetch all remote changes
```

### Clean Up Branches
```bash
git branch -d feature/completed-feature  # Delete local branch (merged)
git branch -D feature/abandoned-feature  # Force delete (unmerged)
git push origin --delete feature/old     # Delete remote branch
```

### View History
```bash
git log --oneline --graph --all          # Visual branch history
git log --oneline -10                    # Last 10 commits
```

---

## Summary

✅ **Always work in feature/bugfix/hotfix branches**  
✅ **Merge features to develop first**  
✅ **Merge develop to main for production releases**  
✅ **Use clear, descriptive branch names**  
✅ **Write meaningful commit messages**  

❌ **Never commit directly to main**  
❌ **Never force push to main or develop**  
❌ **Never push sensitive data (API keys, secrets)**  

---

**Current working branch**: `feature/implement-api-routes`  
**Next**: Implement the 4 API routes as per requirements.
