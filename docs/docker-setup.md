# Running Bharosa with Docker

Everything the platform needs — PostgreSQL with PostGIS, the schema, the API,
and the web console — comes up with one command. You need Docker Desktop and
nothing else: no Python, no Node, no local database.

## Start it

```bash
git clone https://github.com/KallMeNikhil/bharosa.git
cd bharosa
docker compose -f infra/docker-compose.yml up
```

The first run pulls images and builds, so give it a few minutes. It is ready
when the log settles on `Uvicorn running on http://0.0.0.0:8000`.

| What | Where |
| --- | --- |
| Web console | http://localhost:5173 |
| API | http://localhost:8000/api/v1 |
| Interactive API docs | http://localhost:8000/docs |
| Database | `localhost:5432`, database `bharosa` |

Stop it with `Ctrl+C`, or `docker compose -f infra/docker-compose.yml down` from
another terminal. Your data survives both.

## What just happened

Four services start in order, and the order matters:

1. **`db`** — PostGIS 16. On its first boot only, it runs
   `infra/postgres-init.sql`, which installs the PostGIS extension and creates
   the three database roles the platform separates privileges across:
   `bharosa_owner` (owns the tables, runs migrations), `bharosa_app` (the
   tenant-scoped runtime role), and `bharosa_verifier` (public verification
   only).
2. **`migrate`** — applies `alembic upgrade head`, then exits. Row-level
   security policies and table grants exist *only* in the migrations, so the
   schema is unusable until this finishes.
3. **`api`** — the FastAPI backend, started only once the migration has
   succeeded.
4. **`web`** — the Vite dev server, started only once the API reports its
   database reachable.

Source for the API and the console is mounted into the containers, so editing a
file reloads it. You only rebuild when dependencies change.

## First thing to do in the console

Nothing in the console is reachable until a manufacturer exists. Open
http://localhost:5173, go to **Tenant and actor**, and run the demonstration
scenario. It drives the whole platform through the public API — production,
custody, four scans of a diverted pack seconds apart, detection, risk
correlation, and an investigation — and leaves every screen with real data on
it. Every request is recorded in the **API console** with the exact body sent
and returned.

## Common commands

```bash
docker compose -f infra/docker-compose.yml logs -f api
```

```bash
docker compose -f infra/docker-compose.yml exec api pytest
```

```bash
docker compose -f infra/docker-compose.yml exec db psql -U bharosa_admin -d bharosa
```

After changing a dependency in `pyproject.toml` or `package.json`:

```bash
docker compose -f infra/docker-compose.yml up --build
```

## When something is wrong

**Port already in use.** Something else holds 5432, 8000, or 5173 — most often
a PostgreSQL you installed earlier. Stop it, or change the left-hand number in
the `ports:` entry in `infra/docker-compose.yml`.

**`migrate` exited with an error, and the API never started.** That is the
design working: the API refuses to run against an unmigrated schema. Read the
migration log, then retry:

```bash
docker compose -f infra/docker-compose.yml logs migrate
```

**`role "bharosa_owner" does not exist`.** `postgres-init.sql` runs only on a
*brand new* data directory. If the volume was created before that file existed,
the roles were never made. Wipe the volume and start over:

```bash
docker compose -f infra/docker-compose.yml down -v
```

That deletes all local data — which for a development database is exactly what
you want.

**Console loads but every request fails.** The console proxies `/api` to the
`api` service, so this usually means the API container is unhealthy. Check
`docker compose -f infra/docker-compose.yml ps` and look for a status other
than `healthy`.

## Starting completely fresh

```bash
docker compose -f infra/docker-compose.yml down -v
docker compose -f infra/docker-compose.yml up --build
```

## The mobile apps are separate

`consumer_app/` and `distributor_app/` are Expo React Native apps. They run on
a physical phone through Expo Go, not in Docker, and they talk to the API over
your local network rather than through `localhost`.

Start the backend with Docker as above, find your machine's LAN address, and
point the app at it:

```bash
cd consumer_app && npm install && npx expo start
```

Set `EXPO_PUBLIC_API_BASE_URL` in a `.env` file beside `package.json`:

```
EXPO_PUBLIC_API_BASE_URL=http://192.168.1.5:8000/api/v1
```

Use your own address — `localhost` on a phone means the phone. Both apps can
run at once; the distributor scanner is configured for port 8082 so it does not
collide with the consumer app on 8081.

The API container already listens on all interfaces, so a phone on the same
network can reach it. If you are running the backend directly instead, start it
with `--host 0.0.0.0` or the phone will not connect.

`npx expo start --web` runs either app in a browser. The camera and the API are
both unavailable there — a browser blocks cross-origin calls to the backend —
so use it for layout work only.

To produce an installable Android build:

```bash
npm install -g eas-cli
eas build -p android --profile preview
```

One thing worth knowing about the consumer app: the public verification
endpoint answers in a fixed shape and deliberately reveals nothing beyond a
state and a sentence — no risk score, no detector name, no location, nothing
about any other pack. `Registered` means the code is registered and nothing has
been flagged against it. It is not a claim about the liquid inside the bottle,
and no screen says "verified authentic". Scan history stays on the device and
is never uploaded.

## Without Docker

If you would rather run things directly, the database still comes from Docker
and the rest runs on your machine:

```bash
docker compose -f infra/docker-compose.yml up -d db
cd backend && pip install -e ".[dev]"
cp ../.env.example ../.env
alembic upgrade head
uvicorn app.main:app --reload
```

```bash
cd frontend && npm install && npm run dev
```

`.env.example` points at `localhost`, which is correct for this path. The
compose file overrides those values with the `db` hostname for containers.
