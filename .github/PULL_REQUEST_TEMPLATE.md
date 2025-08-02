# Pull Request

## Description
<!-- Describe your changes here -->

## CI Status
- [ ] **Smoke Test**: CI / test-api must be green to merge
- [ ] **Full CI**: Run full CI on this PR (add `[full-ci]` to commit message)

## Notes
- Only **CI / test-api** gates merges (fast, ~30s)
- Heavy jobs (ci-full, eval, perf) run optionally and don't block merges
- To run full CI: add `[full-ci]` to any commit message, or use manual trigger in Actions

## Manual Full CI Trigger
If you want to run the full CI suite without a commit:
1. Go to **Actions** → **CI** workflow
2. Click **Run workflow** button
3. Select branch and run

## Checklist
- [ ] Code follows project style guidelines
- [ ] Tests pass (smoke test at minimum)
- [ ] Documentation updated if needed
- [ ] No breaking changes (or documented if necessary)
