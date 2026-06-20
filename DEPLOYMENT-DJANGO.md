# Deploying the Django Version to Railway

This is the simplest practical way to get the Django UI running on a
real server, with one important wrinkle handled correctly: this app
stores its data in `data/*.csv` files on disk, not a database. Most
"push and deploy" platforms (classic Heroku, in particular) wipe local
files on every restart or redeploy - which would silently delete any
edits you make through the Add/Edit/Delete forms. Railway supports a
**persistent volume**, which is the one thing you must not skip below.

I tested the production startup path locally first (gunicorn + WhiteNoise
+ `DEBUG=0`, the same way it'll run on Railway) before writing this, so
these steps are verified to work, not just theoretical.

## 1. Get your code into a GitHub repo

If it isn't already:
```bash
cd slotting_optimizer
git init
git add .
git commit -m "Initial commit"
```
Create a new repo on GitHub, then:
```bash
git remote add origin https://github.com/your-username/your-repo.git
git push -u origin main
```

## 2. Create the Railway project

1. Go to [railway.app](https://railway.app), sign in with GitHub.
2. **New Project** → **Deploy from GitHub repo** → pick your repo.
3. Railway will try to auto-detect and build immediately - it'll likely
   fail at this point, because it doesn't know which `requirements*.txt`
   to use (this repo intentionally has separate ones per UI) and there's
   no database migrated yet. That's expected - keep going, the settings
   below fix it.

## 3. Set the install & start commands

In your new service → **Settings** → **Deploy**:

- **Custom Install Command**:
  ```
  pip install -r requirements-django.txt
  ```
- **Custom Start Command** (this is also in the repo's `Procfile`, so
  Railway may pick it up automatically - set it explicitly if not):
  ```
  python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn slotting_django.wsgi:application --bind 0.0.0.0:$PORT --workers 1
  ```

  **Why `--workers 1`**: gunicorn normally runs several worker
  *processes* to handle requests in parallel. This app's "database" is
  flat CSV files with no real locking - one worker means every request
  is handled by the same single process, so two saves can never race
  against each other. For the handful of concurrent users this app is
  built for, one worker is both simpler and safer than tuning for
  concurrency this storage layer was never designed for.

## 4. Add a persistent volume (the important part)

In your service → **Settings** → **Volumes** → **New Volume**:

- **Mount path**: `/app/data`

That's it - but don't skip it. Railway builds your app into `/app`
inside the container, so mounting the volume at `/app/data` makes it
exactly overlay the `data/` folder your code already reads and writes
via `app/data_manager.py`, with zero code changes. Without this volume,
every redeploy resets `data/` back to whatever was last committed to
git, silently discarding any edits made through the app.

## 5. Set environment variables

In your service → **Variables**:

| Variable | Value |
|---|---|
| `DJANGO_SECRET_KEY` | a long random string (e.g. generate with `python -c "import secrets; print(secrets.token_urlsafe(50))"`) |
| `DJANGO_DEBUG` | `0` |
| `DJANGO_ALLOWED_HOSTS` | your Railway domain once assigned, e.g. `your-app.up.railway.app` (you can use `*` temporarily to get the first deploy working, then tighten it) |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://your-app.up.railway.app` |

## 6. Deploy

Trigger a redeploy (Railway does this automatically on git push, or use
the dashboard's redeploy button). Check the build logs - you should see
`pip install -r requirements-django.txt` run, then on start: migrations
applying, static files collecting, and gunicorn booting.

Railway will give you a public URL like `https://your-app.up.railway.app`
- once it's confirmed working, go back and set `DJANGO_ALLOWED_HOSTS`
and `DJANGO_CSRF_TRUSTED_ORIGINS` to that exact domain instead of `*`,
and redeploy once more.

## 7. Verify the data actually persists

This is worth checking once, since it's the whole point of step 4:
1. Add a test record through the app (any table).
2. Trigger a redeploy (or just restart the service from the dashboard).
3. Confirm the record is still there afterward.

If it's gone, the volume isn't mounted at the right path - double-check
step 4 says `/app/data` exactly.

## Ongoing updates

Every `git push` to your connected branch triggers an automatic
redeploy. Your `data/*.csv` files are untouched by this (they live on
the volume, not in git), so deploying code changes never resets your
data.

## If you outgrow this

If you ever need more than 1-2 occasional users hitting this hard
enough to matter, or want full control over the server, the natural
next step is a small traditional VPS (DigitalOcean, Hetzner, etc.) with
gunicorn behind nginx and a systemd service - the same `Procfile`
command works there too, you'd just run it directly instead of through
Railway's platform layer. Happy to write that guide in detail if/when
you actually need it; it's more setup for not much benefit at this
scale.
