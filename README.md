# HyLight Demo

Monorepo with **Frontend** (Next.js, Vercel) and **backend** (FastAPI, Docker).

## Structure

```
Frontend/          Next.js 16 + Supabase Auth client
backend/           FastAPI + repository pattern + Pydantic
supabase/          SQL migration for Supabase Postgres
docker-compose.yml Redis + API (local)
```

## Local development

### 1. Supabase (you provide credentials)

Create a project at [supabase.com](https://supabase.com), then:

1. Run `supabase/migrations/001_initial_schema.sql` in the SQL Editor.
2. Enable extension **postgis** (Database → Extensions).
3. Create Storage bucket named **`photos`** (public or private with RLS policies for authenticated uploads).
4. Copy keys into env files (see below).

### 2. Environment files

**backend/.env** (copy from `backend/.env.example`):

| Variable | Where to find it |
|----------|------------------|
| `DATABASE_URL` | Settings → Database → Connection string → URI (use **Transaction pooler** port 6543, prefix with `postgresql+asyncpg://`) |
| `SUPABASE_JWT_SECRET` | Settings → API → JWT Settings → **JWT Secret** |
| `SUPABASE_URL` | Settings → API → Project URL |
| `REDIS_URL` | `redis://localhost:6379/0` when using docker compose |
| `CORS_ORIGINS` | `http://localhost:3000` |

**Frontend/.env.local** (copy from `Frontend/.env.example`):

| Variable | Where to find it |
|----------|------------------|
| `NEXT_PUBLIC_SUPABASE_URL` | Project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Settings → API → **anon public** key |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` |

Optional for AI descriptions (backend only):

| Variable | Use |
|----------|-----|
| `GEMINI_API_KEY` | Google AI Studio key for auto photo descriptions |
| `SUPABASE_SECRET_KEY` or `SUPABASE_SERVICE_ROLE_KEY` | `sb_secret_...` or legacy JWT — server-side storage download (optional; app can use signed URLs from the browser instead) |
| `STORAGE_BUCKET` | `Photos` (match your Supabase bucket name) |

### 3. Start Redis + API

```bash
make up
# API: http://localhost:8000/docs
```

### 4. Start Frontend

```bash
cd Frontend
npm install
npm run dev
# http://localhost:3000
```

## API overview

| Method | Path | Auth |
|--------|------|------|
| GET | `/v1/healthz` | No |
| GET | `/v1/me` | Bearer Supabase JWT |
| POST | `/v1/photos/upload-url` | Bearer |
| POST | `/v1/photos/{id}/finalize` | Bearer |
| GET | `/v1/photos/map/viewport` | Bearer |
| GET | `/v1/photos/{id}` | Bearer |
| POST | `/v1/photos/{id}/comments` | Bearer |

## Deploy

- **Frontend:** Vercel — set the three `NEXT_PUBLIC_*` env vars.
- **Backend:** Build `backend/Dockerfile`, run on ECS/Fargate or any container host with `DATABASE_URL`, `REDIS_URL`, and Supabase secrets.

## What to send me from Supabase

When ready, share (via secure channel, not public git):

1. Project URL  
2. Anon key  
3. Database connection string (pooler URI)  
4. JWT secret  
5. Confirm bucket `photos` exists and upload policy allows authenticated users  
