# Security Remediation Checklist

**Priority**: Fix critical issues before production deployment
**Full Report**: See [SECURITY_AUDIT_REPORT.md](./SECURITY_AUDIT_REPORT.md)

## 🔴 Critical (Do First)

- [ ] **Add non-root user to Dockerfile**
  ```dockerfile
  RUN groupadd -r django && useradd -r -g django django
  RUN chown -R django:django /code
  USER django
  ```
  - Update all stages: runtime-full, runtime-minimal, celery-unified
  - Change EXPOSE from 80 to 8000
  - Test locally before deploying

- [ ] **Enable health checks**
  ```dockerfile
  HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
      CMD curl -f http://127.0.0.1:8000/health/ || exit 1
  ```
  - Uncomment health check in Dockerfile.multistage:133-134
  - Update port from 80 to 8000
  - Verify `/health/` endpoint exists in Django

- [ ] **Add resource limits**
  - CapRover app settings: Memory limit 2GB, CPU limit 2.0
  - Celery app settings: Memory limit 2GB, CPU limit 2.0
  - Document limits in deployment guide

- [ ] **Implement deployment rollback**
  - Add health check after deployment
  - Store previous version before deploy
  - Auto-rollback on health check failure
  - Test rollback mechanism

## 🟡 Medium Priority (Next Sprint)

- [ ] **Add dependency scanning**
  ```yaml
  - name: Python security scan
    run: pip install safety && safety check

  - name: NPM audit
    run: npm audit --production --audit-level=high

  - name: Container scanning
    uses: aquasecurity/trivy-action@master
  ```

- [ ] **Enable image signing**
  ```yaml
  - name: Sign images
    uses: sigstore/cosign-installer@main
  - run: cosign sign --yes $IMAGE_NAME
  ```

- [ ] **Isolate Chromium service**
  - Create separate Docker image for screenshot generation
  - Add network restrictions
  - Run with AppArmor profile

- [ ] **Add network policies**
  - Internal network for database/redis
  - External network only for web service
  - Document network architecture

- [ ] **Improve entrypoint validation**
  - Validate command arguments
  - Fail migrations hard in production
  - Add command allowlist

## ✅ Already Good

- ✅ Multi-stage Docker builds (40% size reduction)
- ✅ Secrets in GitHub Secrets (not committed)
- ✅ SHA-pinned GitHub Actions
- ✅ Minimal base image (python:3.13-slim)
- ✅ Read-only permissions in CI/CD
- ✅ Cache mounts with locking

## 🔍 Verification Commands

```bash
# Test non-root user
docker run --rm IMAGE_NAME whoami  # Should output: django

# Test health check
docker inspect IMAGE_NAME | grep -A 10 Healthcheck

# Check resource limits (in CapRover)
# App Settings → Show Advanced → Resources

# Verify secrets not in git
git log --all --full-history -- .env

# Scan for vulnerabilities
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image IMAGE_NAME
```

## 📊 Risk Reduction

| Phase | Risk Level | Completion |
|-------|------------|------------|
| Current | 🔴 HIGH | 0% |
| Phase 1 Complete | 🟡 MEDIUM | 25% |
| Phase 2 Complete | 🟢 LOW | 75% |
| Phase 3 Complete | 🟢 BEST PRACTICE | 100% |

## 🎯 Target Timeline

- **Week 1**: Critical issues (non-root, health checks, resource limits)
- **Week 2**: Rollback mechanism, dependency scanning
- **Week 3**: Image signing, network policies
- **Week 4**: Chromium isolation, monitoring setup

## 📝 Notes

- Test each change locally before deploying
- Update documentation as you go
- Schedule security review after Phase 1
- Consider compliance requirements (CIS, OWASP)
