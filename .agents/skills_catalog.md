# Agent Skills Catalog

Catalog of custom Antigravity agent skills available in `apt`.

| Skill | Description | Task / Command |
|---|---|---|
| [`add-app`](skills/add-app/SKILL.md) | Onboard app to APT repo: configure deb packaging, release publishing, local discovery, and set `APT_REPO_TOKEN` secret | `/add-app <app>` |
| [`deploy-apt-repo`](skills/deploy-apt-repo/SKILL.md) | Trigger manual execution of `.github/workflows/deploy-repo.yml` to generate metadata and deploy to GitHub Pages | `rtk gh workflow run deploy-repo.yml \| cat` |
