# Development Workflow Guide

## Quick Fix for Pre-commit Hook Failures

If you encounter pre-commit hook failures (like "ruff ... exit code 1"), here's the 60-second fix:

```bash
# 1) See what's wrong
git status -sb

# 2) Auto-fix style/lint issues
make fix

# 3) Re-run the repo's quick gate (optional but recommended)
pytest -q tests/ci_smoke_test.py || true

# 4) Commit & push
git add -A
git commit -m "chore: ruff fixes to unblock commits" || git commit -m "wip: bypass hook" --no-verify
git push -u origin "$(git rev-parse --abbrev-ref HEAD)"
```

## Common Issues and Solutions

### Pre-commit Hooks Blocking Commits

**Problem**: Ruff, black, or other pre-commit hooks fail and prevent commits.

**Solutions**:
1. **Auto-fix**: Run `make fix` to automatically fix most issues
2. **Manual bypass**: Use `git commit --no-verify` for urgent commits
3. **Skip specific hooks**: Set environment variable `SKIP=ruff` before commit

### Git Status Bar Shows Orange

**Problem**: Cursor/VS Code shows orange status bar indicating Git needs attention.

**Solutions**:
1. **Unpushed commits**: Run `git push`
2. **Merge/rebase in progress**: Run `git rebase --continue` or `git rebase --abort`
3. **Restricted Mode**: Click the shield icon and "Trust" the folder
4. **Ahead/behind**: Check the right side of status bar for ↑N ↓M indicators

### Git Lock Issues

**Problem**: Git complains about locks or index issues.

**Solution**:
```bash
rm -f .git/index.lock .git/HEAD.lock
```

## Development Best Practices

### 1. Use the Fix Target

Before committing, always run:
```bash
make fix
```

This will:
- Run `ruff check --fix --unsafe-fixes .` to fix linting issues
- Run `black .` to format code

### 2. Pre-commit Hook Strategy

The repository uses a **soft-fail locally, hard-fail in CI** approach:

- **Local development**: Pre-commit hooks provide warnings but can be bypassed
- **CI/CD**: All checks are enforced to maintain code quality
- **Bypass when needed**: Use `--no-verify` for urgent commits

### 3. Commit Message Guidelines

Use conventional commit format:
- `feat:` for new features
- `fix:` for bug fixes
- `chore:` for maintenance tasks
- `docs:` for documentation changes
- `test:` for test changes

### 4. Branch Management

- Create feature branches from `main`
- Use descriptive branch names: `feat/feature-name`
- Set up upstream tracking: `git push -u origin branch-name`
- Keep branches focused and small

### 5. Testing Strategy

**Local Testing**:
```bash
# Quick smoke test
pytest -q tests/ci_smoke_test.py

# Full test suite
pytest tests/

# CI simulation
make ci-local
```

**CI Gates**:
- `test-api`: Basic API functionality (required)
- `ci-full`: Full test suite (optional)
- `eval`: Evaluation metrics (optional)
- `perf`: Performance benchmarks (optional)

## Troubleshooting

### Ruff Issues

**Common ruff errors**:
- `E721`: Use `isinstance()` instead of `type()` comparison
- `E702`: Multiple statements on one line
- `F841`: Unused variable
- `F821`: Undefined name

**Fix with**:
```bash
ruff check --fix --unsafe-fixes .
```

### Black Formatting Issues

**Fix with**:
```bash
black .
```

### Import Issues

**Common causes**:
- Missing `__init__.py` files
- Incorrect import paths
- Missing dependencies

**Check with**:
```bash
python -c "import ae2"
```

### Test Failures

**Debug with**:
```bash
# Verbose output
pytest -v tests/test_specific.py

# Stop on first failure
pytest -x tests/

# Show local variables on failure
pytest -l tests/
```

## Environment Setup

### Required Tools

1. **Python 3.10+**
2. **Git**
3. **Make** (for `make fix` target)
4. **Pre-commit hooks**: `pre-commit install`

### Optional Tools

1. **Docker**: For containerized development
2. **jq**: For JSON processing
3. **curl**: For API testing

### Environment Variables

```bash
# Development
export ENVIRONMENT=development
export DEBUG=true
export ENABLE_DENSE=0
export AE_INDEX_DIR=$(pwd)/data/index
export AE_BIND_PORT=8001

# Skip pre-commit hooks (when needed)
export SKIP=ruff
```

## Performance Considerations

### Local Development

- Use `ENABLE_DENSE=0` for faster startup
- Use sample datasets for quick testing
- Disable metrics in development: `AE_ENABLE_METRICS=0`

### CI/CD

- Full evaluation runs in CI
- Performance benchmarks in separate job
- Artifacts preserved for analysis

## Contributing Guidelines

1. **Fork and clone** the repository
2. **Create a feature branch** from `main`
3. **Make changes** following the coding standards
4. **Run tests** locally before pushing
5. **Use conventional commits** for commit messages
6. **Push and create a PR** with clear description
7. **Ensure CI passes** before requesting review

## Emergency Procedures

### Bypass All Checks

For emergency fixes that need immediate deployment:

```bash
# Skip all pre-commit hooks
SKIP=all git commit -m "emergency: critical fix" --no-verify

# Force push (use with caution)
git push --force-with-lease
```

### Rollback Changes

```bash
# Soft reset (keep changes in working directory)
git reset --soft HEAD~1

# Hard reset (discard all changes)
git reset --hard HEAD~1
```

### Recover from Bad State

```bash
# Clean working directory
git clean -fd

# Reset to last known good state
git reset --hard origin/main

# Re-apply your changes
git cherry-pick <commit-hash>
```

## Support

For issues not covered in this guide:

1. Check the main README.md
2. Review existing issues and PRs
3. Create a new issue with detailed information
4. Contact the maintainers through the project channels 