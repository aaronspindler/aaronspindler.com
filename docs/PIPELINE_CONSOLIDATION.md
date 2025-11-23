# Pipeline Consolidation Guide

## Overview

This guide explains how to migrate from separate `test.yml` and `deploy.yml` workflows to a single consolidated `pipeline.yml` workflow.

## 📊 Before vs After

### Before (2 Workflows)

```
test.yml (triggered on push/PR)
  ├─ Build test image
  ├─ Run tests
  ├─ Build production images
  └─ Tag production images
       └─ Triggers...

deploy.yml (triggered by test.yml completion)
  └─ Deploy to CapRover
```

**Issues:**
- Complex workflow dependencies
- `workflow_run` trigger adds latency (2-3 minutes wait)
- Harder to debug deployment failures
- Separate status checks in GitHub UI

### After (1 Workflow)

```
pipeline.yml (single unified workflow)
  ├─ Build test image
  ├─ Build production images (parallel)
  ├─ Run tests
  ├─ Tag production images
  ├─ Deploy to CapRover
  └─ Pipeline summary
```

**Benefits:**
- ✅ Simpler, easier to understand
- ✅ Faster deployments (no workflow_run latency)
- ✅ Single status check in GitHub UI
- ✅ Better visibility into entire pipeline
- ✅ Easier to debug issues

## 🚀 Migration Steps

### Step 1: Test the New Pipeline

First, let's test the new pipeline without disrupting your current setup:

```bash
# The new pipeline.yml is already created
# It will run alongside your existing workflows

# Push a commit to test
git add .github/workflows/pipeline.yml docs/PIPELINE_CONSOLIDATION.md
git commit -m "feat: add consolidated pipeline workflow"
git push origin main
```

**What to watch:**
- Both `pipeline.yml` and `test.yml` will run
- `deploy.yml` will also trigger after `test.yml`
- Verify the new pipeline completes successfully

### Step 2: Verify Pipeline Behavior

Check the Actions tab and verify:

1. **On Pull Requests:**
   - ✅ Tests run
   - ✅ Test images are built
   - ❌ Production images are NOT built
   - ❌ Deployment does NOT happen

2. **On Main Branch Push:**
   - ✅ Tests run
   - ✅ Production images are built
   - ✅ Images are tagged with commit SHA
   - ✅ Deployment to CapRover succeeds
   - ✅ Pipeline summary shows success

### Step 3: Update Cleanup Workflow Reference

The cleanup workflow currently references "Pipeline - Tests". Update it:

```yaml
# .github/workflows/cleanup-containers.yml
on:
  workflow_run:
    workflows: ["Pipeline - Build, Test, Deploy"]  # Changed from "Pipeline - Tests"
    types: [completed]
    branches: [main]
```

### Step 4: Disable Old Workflows

Once the new pipeline is verified, disable the old workflows:

**Option A: Rename (Recommended for rollback safety)**
```bash
mv .github/workflows/test.yml .github/workflows/test.yml.disabled
mv .github/workflows/deploy.yml .github/workflows/deploy.yml.disabled
git add .github/workflows/
git commit -m "chore: disable old test and deploy workflows (use pipeline.yml)"
git push origin main
```

**Option B: Delete (Clean removal)**
```bash
git rm .github/workflows/test.yml .github/workflows/deploy.yml
git commit -m "chore: remove old workflows (consolidated into pipeline.yml)"
git push origin main
```

### Step 5: Update Repository Settings

Update branch protection rules:

1. Go to: `Settings → Branches → Branch protection rules → main`
2. Update "Require status checks to pass":
   - ❌ Remove: `test-suite` (from old test.yml)
   - ✅ Add: `test-suite` (from new pipeline.yml)
   - ✅ Add: `deploy` (optional, if you want to require successful deployment)

## 🎯 Key Features of Consolidated Pipeline

### 1. Conditional Deployment

```yaml
deploy:
  if: github.ref == 'refs/heads/main' && needs.tag-production-images.result == 'success'
```

- **PRs:** Tests run, but NO deployment
- **Main:** Full pipeline including deployment

### 2. Smart Concurrency Control

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: ${{ github.ref != 'refs/heads/main' }}
```

- **PRs:** Cancels old runs on new push (fast feedback)
- **Main:** Never cancels (safe deployments)

### 3. Parallel Execution

```yaml
build-production-images:
  runs-on: ubuntu-latest
  if: github.ref == 'refs/heads/main'

test-suite:
  needs: [build-test-image]
```

- Production images build while tests run
- Saves ~5-8 minutes on main branch

### 4. Clear Pipeline Stages

The workflow has distinct stages:
1. **Build** - Create images
2. **Test** - Validate code
3. **Tag** - Finalize production images
4. **Deploy** - Release to production
5. **Cleanup** - Remove old artifacts

### 5. Pipeline Summary

```yaml
pipeline-summary:
  needs: [test-suite, deploy]
```

Provides clear status at the end:
- ✅ All green → Deployment successful
- ❌ Any red → Shows exactly what failed

## 📈 Performance Comparison

### Old Setup (2 Workflows)

```
Push to main
  ├─ test.yml starts         (0:00)
  ├─ Tests complete          (15:00)
  ├─ Images tagged           (18:00)
  ├─ workflow_run wait       (20:00) ⏰ 2min wait
  ├─ deploy.yml starts       (20:00)
  └─ Deployment complete     (25:00)

Total: ~25 minutes
```

### New Setup (1 Workflow)

```
Push to main
  ├─ Build test image        (0:00)
  ├─ Build prod images       (0:00) ⚡ Parallel
  ├─ Tests complete          (15:00)
  ├─ Images tagged           (18:00)
  └─ Deployment complete     (23:00)

Total: ~23 minutes (8% faster)
```

**Time saved:** ~2 minutes per deployment

## 🔧 Troubleshooting

### Issue: Both workflows run after migration

**Cause:** Old workflows are still enabled

**Solution:**
```bash
# Disable old workflows
mv .github/workflows/test.yml .github/workflows/test.yml.disabled
mv .github/workflows/deploy.yml .github/workflows/deploy.yml.disabled
```

### Issue: Deployment fails with "No such image"

**Cause:** Image tagging step may have failed

**Solution:**
Check the `tag-production-images` job logs. The image should be:
```
ghcr.io/aaronspindler/aaronspindler.com-web:abc123def
ghcr.io/aaronspindler/aaronspindler.com-celery:abc123def
```

### Issue: Tests pass but deployment is skipped

**Cause:** Condition not met (not on main or tests failed)

**Solution:**
Verify:
1. You're pushing to `main` branch
2. `test-suite` job shows as "success"
3. Check job conditions in Actions tab

## 🎨 Customization

### Add Deployment Approval

Add manual approval before deployment:

```yaml
deploy:
  needs: [tag-production-images]
  environment:
    name: production
    url: https://aaronspindler.com
```

Then configure environment protection rules in Settings → Environments.

### Deploy Only Specific Service

Temporarily deploy only web:

```yaml
strategy:
  matrix:
    service:
      - name: web
        token: CAPROVER_WEB_APP_TOKEN
        app_name: CAPROVER_WEB_APP_NAME
      # - name: celery  # Commented out
```

### Add Deployment Notifications

```yaml
- name: Notify deployment success
  if: success()
  run: |
    curl -X POST "${{ secrets.SLACK_WEBHOOK }}" \
      -d '{"text":"✅ Deployed ${{ github.sha }} to production"}'
```

## 📝 Rollback Plan

If you need to rollback to the old workflows:

```bash
# Disable new workflow
mv .github/workflows/pipeline.yml .github/workflows/pipeline.yml.disabled

# Re-enable old workflows
mv .github/workflows/test.yml.disabled .github/workflows/test.yml
mv .github/workflows/deploy.yml.disabled .github/workflows/deploy.yml

git add .github/workflows/
git commit -m "chore: rollback to separate test/deploy workflows"
git push origin main
```

## 🎓 Best Practices

1. **Test First:** Always test the new pipeline with the old one still active
2. **Monitor Closely:** Watch the first few deployments carefully
3. **Keep Backups:** Rename old workflows instead of deleting (easy rollback)
4. **Update Docs:** Update any deployment documentation to reference the new workflow
5. **Team Communication:** Notify team members about the workflow change

## 📚 Additional Resources

- [GitHub Actions Workflow Syntax](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)
- [Workflow Concurrency](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#concurrency)
- [Job Dependencies](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#jobsjob_idneeds)
