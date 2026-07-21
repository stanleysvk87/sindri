# Contributing

Sindri started as a personal homelab tool and is maintained by one
person. Contributions are welcome, but please open an issue to discuss
anything non-trivial before sending a pull request — it saves both of
us time if the direction doesn't fit.

## Local development

```bash
# backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest tests/ -v

# frontend
cd frontend
npm ci
npm run dev     # local dev server against a running backend
npm run lint
npm run build
```

Docker isn't required for backend/frontend development on their own —
see `docker-compose.yml` for how the two are wired together in
production, and `docs/*.md` for how each optional feature (AI, sandbox,
remote execution) is gated and why.

## Before opening a pull request

- `python -m pytest backend/tests/ -v` passes.
- `npm run lint && npm run build` passes in `frontend/`.
- New backend behavior that touches auth, SSH, subprocess calls, path
  handling, or the Docker socket should come with a test — see
  `backend/tests/` for the existing patterns (e.g.
  `test_import_containment.py`, `test_remote_exec_safety.py`).
- If you're touching a feature that's off by default (AI, sandbox,
  remote execution), keep it off by default — that's a deliberate
  design choice, not an oversight, see the relevant `docs/*.md`.

## Reporting bugs vs. security issues

Regular bugs: open a GitHub issue. Security issues: see
[`SECURITY.md`](./SECURITY.md) instead — please don't file those as a
public issue.
