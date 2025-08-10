# GitHub Release Guide

## Creating a Release

### 1. Update Version
```bash
echo "4.2.3" > VERSION
git add VERSION
git commit -m "chore: Bump version to 4.2.3"
```

### 2. Create Tag
```bash
git tag -a v4.2.3 -m "Release v4.2.3"
git push origin v4.2.3
```

### 3. GitHub Release
```bash
gh release create v4.2.3 \
  --title "v4.2.3: Security Updates" \
  --notes-file docs/releases/RELEASE_NOTES_v4.2.3.md \
  --draft
```

### 4. Attach Assets (Optional)
```bash
gh release upload v4.2.3 dist/*.whl
```

### 5. Publish
```bash
gh release edit v4.2.3 --draft=false
```

## Release Checklist
- [ ] Tests passing
- [ ] Version bumped
- [ ] Release notes written
- [ ] Security scan clean
- [ ] Documentation updated
- [ ] Tag created
- [ ] GitHub release published