---
layout: default
title: GitHub Pages
permalink: /github-pages.html
---

# Publish this repo’s docs on GitHub Pages

This documentation lives in **`docs/`** at the **root of the agent repository** (the repo that contains only `AI_receptionist_agent` content when you split remotes).

## Steps

1. Push `docs/` and `_config.yml` to your default branch.
2. **Settings** → **Pages** → **Build and deployment** → Source: **Deploy from a branch** → Branch **main**, folder **`/docs`** → Save.
3. After the build, open the URL shown (e.g. `https://<user>.github.io/<agent-repo>/`).

## `baseurl`

If the site path is not the domain root, set in `docs/_config.yml`:

```yaml
baseurl: "/your-agent-repo-name"
url: "https://your-username.github.io"
```

[← Home]({{ "/" | relative_url }})
