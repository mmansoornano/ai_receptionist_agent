---
layout: default
title: GitHub Pages
---

## Why links were 404

GitHub **project Pages** serves your site at:

`https://<user>.github.io/<repository-slug>/`

Every internal URL must include that **prefix**. In Jekyll that is the **`baseurl`** in **`docs/_config.yml`**.

**Edit these three lines** when you fork or rename the repo:

```yaml
baseurl: "/ai_receptionist_agent"   # leading slash, no trailing slash
url: "https://mmansoornano.github.io"
github_repo: mmansoornano/ai_receptionist_agent
```

After changing **`baseurl`**, push and wait for the Pages build. Navigation uses Jekyll’s {% raw %}`{% link %}`{% endraw %} tag so paths stay correct relative to **`baseurl`**.

## Enable Pages

1. Repository **Settings** → **Pages**.
2. **Build and deployment** → Source: **Deploy from a branch**.
3. Branch: **`main`**, folder: **`/docs`** → Save.

Build logs: **Actions** tab (or the Pages settings banner).

## Optional: user/org site (`*.github.io` without repo path)

If you ever publish to a **root** domain site, set **`baseurl: ""`** and adjust **`url`** accordingly.

## Local preview

Install Ruby + Jekyll, then from the **repository root** (not only `docs/`):

```bash
bundle init
bundle add webrick jekyll
bundle exec jekyll serve --source docs --destination _site_docs --baseurl "/ai_receptionist_agent"
```

Then open `http://127.0.0.1:4000/ai_receptionist_agent/` (match `--baseurl` to your real repo slug). To preview at the site root instead, use `--baseurl ""` and expect nav links to differ from production project Pages.
