# Deploy & Operations Runbook

How Sprout is deployed and how to operate it. Read this before touching the
deployment, and *especially* before a restore.

> _Written completely by AI._

---

## What this is

One process: **FastAPI (uvicorn) serves both the static SvelteKit frontend and
the `/api` JSON endpoints.** The frontend is built (`adapter-static`) into
`web/build/`, which FastAPI serves with an SPA fallback. There is no separate
Node server.

- **Host:** Railway (single service)
- **Data:** SQLite at `/data/portfolio.db` on a Railway **volume** = the source of truth
- **Backups:** daily snapshot to Cloudflare R2, 30-day rolling window

```
Browser ──> Railway service (one uvicorn process)
                 ├── /            → web/build/ (static SvelteKit shell, SPA)
                 └── /api/*        → FastAPI JSON
                         └── reads/writes /data/portfolio.db (volume)
                                  └── api/backup.py → daily snapshot → R2
```

---

## Required configuration (Railway → Variables)

These are **load-bearing**. If the app 500s after a deploy, the first thing to
check is that all of these exist.

| Variable | Value | Why |
|---|---|---|
| `PORTFOLIO_DB` | `/data/portfolio.db` | Points the app at the volume. **Without it, the app uses an ephemeral path, ignores the volume, and 500s.** |
| `PORTFOLIO_PRICES` | `/data/prices` | yfinance price cache on the volume (regenerable, but persisting it = fast boots). |
| `SPROUT_PASSWORD` | any strong passphrase | Owner fallback sign-in, and the session-signing key when `SPROUT_SECRET` is unset (api/auth.py). **With no password AND no Google client, the whole portfolio is public.** Rotating it logs every device out. |
| `GOOGLE_CLIENT_ID` | _(Google Cloud console)_ | Enables "Continue with Google". Unset = the sign-in screen offers only the password. |
| `GOOGLE_CLIENT_SECRET` | _(Google Cloud console)_ | OAuth code exchange. |
| `SPROUT_PUBLIC_URL` | `https://<your-app>.up.railway.app` | Builds the OAuth `redirect_uri`. **Load-bearing:** Railway terminates TLS upstream so the app sees plain `http`; without this the callback URL won't match what Google has registered and every sign-in fails. No trailing slash. |
| `SPROUT_OWNER_EMAIL` | `yazan@bu.edu` | The account that the password fallback signs into, and the one email allowed to claim the pre-OAuth `user_id = 1` (which owns all existing trade history). |
| `SPROUT_ALLOWED_EMAILS` | `a@gmail.com,b@gmail.com` | Comma-separated invite list. **Anyone not on it (or on `SPROUT_OWNER_EMAIL`) is refused and no account is created.** Without it, any Google account could provision a portfolio here. |
| `SPROUT_SECRET` | _(optional, random 32+ chars)_ | Session cookie signing key. Falls back to `SPROUT_PASSWORD`. Set it if you want to rotate the password without logging everyone out. |
| `R2_ENDPOINT` | `https://<account-id>.r2.cloudflarestorage.com` | Cloudflare R2 S3 endpoint (account-level, **no bucket name in it**). |
| `R2_ACCESS_KEY_ID` | _(from R2 API token)_ | Backup auth. |
| `R2_SECRET_ACCESS_KEY` | _(from R2 API token)_ | Backup auth (shown only once at token creation). |
| `R2_BUCKET` | `sprout-backups` | Bucket **name** only. |

**Volume:** mounted at **`/data`**. The volume is region-bound — changing the
service region gives you a fresh empty volume (would require re-seeding).

---

## Build & run config (in the repo)

- **`nixpacks.toml`** — build recipe. Installs Python deps + the `portfolio`
  package (`.venv/bin/pip install .`) and builds the frontend (`npm --prefix web ci && run build`).
- **`railway.json`** — run config. Start command:
  ```
  PYTHONPATH=src .venv/bin/uvicorn api.main:app --host 0.0.0.0 --port $PORT --workers 1
  ```
  **Single worker / single replica is required** — `api/state.py` keeps an
  in-process snapshot cache, so a second instance would serve stale data.

---

## Deploying

Railway auto-deploys on push to `main` (and on any Variables change).

```bash
git push          # → Railway rebuilds (nixpacks) and restarts
```

The **volume persists across redeploys** — `/data/portfolio.db` is safe. You do
not re-seed on a normal deploy.

---

## Setting up Google sign-in (one time)

1. Google Cloud console → **APIs & Services → Credentials → Create credentials →
   OAuth client ID**, type **Web application**.
2. **Authorized redirect URIs** — add both, exactly (no trailing slash):
   ```
   https://<your-app>.up.railway.app/api/auth/google/callback
   http://localhost:8000/api/auth/google/callback
   ```
   These must match byte-for-byte or Google returns `redirect_uri_mismatch`.
   Authorized *JavaScript origins* are not needed — this is a server-side flow.
3. On the OAuth **consent screen**, External + Testing is fine for a handful of
   users; add each person under **Test users**.
4. Set the `GOOGLE_*`, `SPROUT_PUBLIC_URL`, `SPROUT_OWNER_EMAIL` and
   `SPROUT_ALLOWED_EMAILS` variables above, then deploy.

### First sign-in after enabling OAuth — order matters

`user_id = 1` predates OAuth and owns **all existing trade history**, with no
email on it. The first sign-in by `SPROUT_OWNER_EMAIL` claims that row; anyone
else signing in first just gets a fresh empty account (they cannot take it).

1. **Back up the volume DB first** (see Backups below) — this deploy migrates
   the `users` table.
2. Sign in as `SPROUT_OWNER_EMAIL` **before inviting anyone**, and confirm the
   portfolio still shows its full history.
3. Verify the claim landed on the original row, not a new one:
   ```bash
   railway ssh "sqlite3 /data/portfolio.db 'SELECT user_id,email,google_sub FROM users'"
   ```
   The owner must be `user_id = 1`. If they came back as `2`, stop and restore
   from backup rather than re-pointing rows by hand.
4. Then add friends to `SPROUT_ALLOWED_EMAILS`. Each gets an empty portfolio on
   first sign-in; all data is scoped by `user_id` and never shared.

Note the session cookie format changed with OAuth, so **the first deploy signs
every existing device out once**. That is expected.

---

## Seeding the DB (first time, or after recreating the volume)

The volume starts empty. Upload the local DB once (it is tiny, base64 over SSH
avoids binary corruption):

```bash
# from the repo root, with the Railway CLI linked (railway link)
base64 -i data/portfolio.db | railway ssh "base64 -d > /data/portfolio.db"
railway ssh "ls -la /data/portfolio.db"   # verify size matches local
```

Then restart the service so it reads the seeded data.

> Note: `data/` is git-ignored — the real DB and prices never go in git.

---

## Backups (Cloudflare R2)

`api/backup.py` runs inside the app (started in `main.py` lifespan, **only if
the `R2_*` vars are set**):

- ~60s after boot, then every 24h: `VACUUM INTO` a consistent snapshot and
  upload to R2 as `portfolio-YYYY-MM-DD.db`.
- **30-day rolling window** — snapshots older than 30 days are deleted by date.
- Best-effort: a backup failure is logged and swallowed; it can never crash the
  app or block startup.

**Verify it's working:** after a deploy, check Railway logs for
`backup uploaded: s3://sprout-backups/portfolio-...` and confirm the object
appears in the R2 bucket.

### Restore (volume lost, or to undo a bad data change)

1. Download the desired snapshot from R2 (latest, or an earlier day).
2. Seed it back exactly like the initial seed:
   ```bash
   base64 -i portfolio-YYYY-MM-DD.db | railway ssh "base64 -d > /data/portfolio.db"
   ```
3. Restart the service.

---

## Data model (don't break this)

- **Cloud SQLite is the source of truth.** All writes go through the dashboard
  (`/api`) — a single write path, which is what makes SQLite safe here (and lets
  a second user join).
- **The laptop copy is read-only / disposable.** Pull a copy to backtest, but
  **never write trades locally and push the file up** — it would clobber
  trades entered from the phone.
- **`data/prices` is a regenerable cache** (rebuilt from yfinance). Losing it
  costs only a slow first boot.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| App 500s on `/api/*` after deploy | `PORTFOLIO_DB` / `PORTFOLIO_PRICES` not set, or empty DB | Confirm the env vars; confirm `/data/portfolio.db` exists (seed if not) |
| Frontend loads but no data, slow first load | prices cache rebuilding from yfinance | Wait; it self-populates (optionally seed `data/prices`) |
| Build fails | nixpacks didn't build frontend, or a dep is missing | Read the Railway build log; check `nixpacks.toml` ran `npm build` |
| No `backup uploaded` in logs | `R2_*` vars missing | Add the four R2 variables |
| Stale / inconsistent data across requests | more than one instance running | Ensure `--workers 1` and `numReplicas: 1` |

---

## Local development

One command — starts both servers, Ctrl-C stops both:

```bash
./dev.sh            # FastAPI :8000 + Vite :5173 → open http://localhost:5173
```

Or run them manually in two terminals:

```bash
# backend (from repo root)
PYTHONPATH=src .venv/bin/python -m uvicorn api.main:app --reload --port 8000

# frontend (separate terminal) — dev server on :5173, proxies /api to :8000
cd web && npm run dev
```

Use `python -m uvicorn` (not the bare `.venv/bin/uvicorn` console script): venv
scripts hardcode an absolute path in their shebang, so they break if the project
folder is renamed/moved. The `python` symlink + `-m` form is rename-proof. Same
for pip: `.venv/bin/python -m pip ...`. (To fully reset a stale venv:
`rm -rf .venv && python3 -m venv .venv && .venv/bin/python -m pip install -e .`)

For a production-like single-process run locally: `npm --prefix web run build`,
then start uvicorn — it will serve `web/build/` directly. Backups stay disabled
locally (no `R2_*` vars).

> Note: this venv-shebang issue is **local only**. Railway builds a fresh venv
> at `/app/.venv` on each deploy, so its scripts always match — the live site is
> unaffected.
