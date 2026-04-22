---
layout: default
title: GitHub Pages
---

## Why links were 404

GitHub **project Pages** serves your site at:

`https://<user>.github.io/<repository-slug>/`

Every internal URL must include that **prefix**. In Jekyll that is the **`baseurl`** in **`docs/_config.yml`**.

**Edit these lines** when you fork or rename the repo (keep **`url`**, **`baseurl`**, and **`canonical_docs_url`** aligned):

```yaml
baseurl: "/ai_receptionist_agent"   # leading slash, no trailing slash
url: "https://mmansoornano.github.io"
canonical_docs_url: "https://mmansoornano.github.io/ai_receptionist_agent"  # no trailing slash
github_repo: mmansoornano/ai_receptionist_agent
```

Nav, home-page cards, cross-links, and **architecture diagram** `<img>` URLs use **`canonical_docs_url`** so they resolve under the project path (for example **`…/ai_receptionist_agent/assets/img/agent-architecture.svg`**). Plain **`relative_url`** on images can end up as **`/assets/...`** on the wrong host path and **break on GitHub Pages**. For a local Jekyll preview, temporarily point **`canonical_docs_url`** at your dev origin (for example `http://127.0.0.1:4000/ai_receptionist_agent`).

**`relative_url`** is still used for **CSS** under **`/assets/css/`**, so **`baseurl`** must stay correct for styling.

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
