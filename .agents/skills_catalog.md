# Agent Skills Catalog

Catalog of custom Antigravity agent skills available in `apt`.

| Skill | Description | Task / Command |
|---|---|---|
| [`deploy-apt-repo`](skills/deploy-apt-repo/SKILL.md) | Trigger manual execution of `.github/workflows/deploy-repo.yml` to generate metadata and deploy to GitHub Pages | `rtk gh workflow run deploy-repo.yml \| cat` |
