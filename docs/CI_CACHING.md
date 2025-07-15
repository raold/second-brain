# CI Caching Strategy

This document explains the comprehensive caching strategy implemented in our GitHub Actions CI pipeline to significantly reduce build times.

## 🚀 Performance Improvements

With these caching optimizations, you can expect:
- **50-80% reduction** in CI run times
- **Faster dependency installation** through pip caching
- **Parallel job execution** for linting and testing
- **Intelligent cache invalidation** based on file changes

## 📦 What We Cache

### 1. Pip Dependencies (`~/.cache/pip`)
- **What**: Downloaded package wheels and source distributions
- **Key**: Based on `requirements.txt` hash
- **Benefit**: Avoids re-downloading packages when requirements haven't changed

### 2. Pip Packages (`~/.local`)
- **What**: Installed packages in user directory
- **Key**: Based on `requirements.txt` hash
- **Benefit**: Faster package installation when dependencies are cached

### 3. Ruff Cache (`.ruff_cache`)
- **What**: Linting results and parsed ASTs
- **Key**: Based on `ruff.toml` and `pyproject.toml` hashes
- **Benefit**: Faster linting on subsequent runs

### 4. Pytest Cache (`.pytest_cache`)
- **What**: Test discovery results and collection metadata
- **Key**: Based on `pytest.ini` and `pyproject.toml` hashes
- **Benefit**: Faster test discovery and collection

## 🔄 Cache Invalidation Strategy

Caches are automatically invalidated when:
- `requirements.txt` changes (pip caches)
- `ruff.toml` or `pyproject.toml` changes (ruff cache)
- `pytest.ini` or `pyproject.toml` changes (pytest cache)
- Cache keys include file hashes for precise invalidation

## 🏗️ Job Structure

### Setup Job
- Installs all dependencies once
- Generates shared cache key
- Provides cache key to dependent jobs

### Lint Job (Parallel)
- Runs ruff linting
- Uses shared pip cache from setup job
- Caches ruff-specific results

### Test Job (Parallel)
- Runs pytest with coverage
- Uses shared pip cache from setup job
- Caches pytest-specific results

## 📊 Expected Performance Gains

| Component | Before | After | Improvement |
|-----------|--------|-------|-------------|
| Dependency Installation | 2-3 minutes | 30-60 seconds | 60-75% |
| Linting | 30-60 seconds | 10-20 seconds | 50-70% |
| Test Discovery | 15-30 seconds | 5-10 seconds | 50-70% |
| **Total CI Time** | **4-6 minutes** | **1.5-2.5 minutes** | **50-70%** |

## 🔧 Cache Configuration Details

### Pip Cache
```yaml
- name: Cache pip dependencies
  uses: actions/cache@v4
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
    restore-keys: |
      ${{ runner.os }}-pip-
```

### Ruff Cache
```yaml
- name: Cache ruff cache
  uses: actions/cache@v4
  with:
    path: .ruff_cache
    key: ${{ runner.os }}-ruff-${{ hashFiles('**/ruff.toml', '**/pyproject.toml') }}
    restore-keys: |
      ${{ runner.os }}-ruff-
```

### Pytest Cache
```yaml
- name: Cache pytest cache
  uses: actions/cache@v4
  with:
    path: .pytest_cache
    key: ${{ runner.os }}-pytest-${{ hashFiles('**/pytest.ini', '**/pyproject.toml') }}
    restore-keys: |
      ${{ runner.os }}-pytest-
```

## 🛠️ Local Development

To benefit from similar caching locally:

1. **Pip Cache**: Already enabled by default in `~/.cache/pip`
2. **Ruff Cache**: Automatically created in `.ruff_cache/`
3. **Pytest Cache**: Automatically created in `.pytest_cache/`

## 📈 Monitoring Cache Performance

You can monitor cache effectiveness in GitHub Actions:
1. Go to your repository's Actions tab
2. Click on a workflow run
3. Look for cache hit/miss indicators in the logs
4. Cache hits show "Cache restored from key: ..."
5. Cache misses show "Cache not found for input keys: ..."

## 🔍 Troubleshooting

### Cache Not Working
1. Check if cache keys are changing unexpectedly
2. Verify file paths in cache configuration
3. Ensure cache directories are not in `.gitignore` (they should be)

### Cache Size Issues
- GitHub Actions has a 10GB cache limit per repository
- Old caches are automatically cleaned up
- Monitor cache usage in repository settings

### Performance Issues
1. Check if dependencies are being reinstalled unnecessarily
2. Verify cache keys are stable between runs
3. Consider splitting large dependency sets

## 🎯 Best Practices

1. **Keep cache keys stable**: Only change when dependencies actually change
2. **Use specific paths**: Cache only what's necessary
3. **Monitor cache hits**: Track cache effectiveness over time
4. **Clean up old caches**: Remove unused cache entries periodically
5. **Test cache invalidation**: Ensure caches update when needed

## 📚 Additional Resources

- [GitHub Actions Cache Documentation](https://docs.github.com/en/actions/using-workflows/caching-dependencies-to-speed-up-workflows)
- [actions/cache Action](https://github.com/actions/cache)
- [Python Caching Best Practices](https://docs.python.org/3/library/functools.html#functools.lru_cache) 
- [Testing Guide](./TESTING.md) 