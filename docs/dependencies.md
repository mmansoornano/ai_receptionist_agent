---
layout: default
title: Dependencies
permalink: /dependencies.html
---

# Dependencies (agent repo)

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

`requirements.txt` uses lower bounds. For a **frozen** demo snapshot:

```bash
pip freeze > requirements.lock.txt
```

Commit `requirements.lock.txt` when you want reproducible installs for a client date.

[← Home]({{ "/" | relative_url }})
