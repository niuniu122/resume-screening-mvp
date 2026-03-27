# Backend Deployment Notes

This backend supports two runtime storage modes:

- `local`: saves uploads under `backend/storage/`
- `oss`: saves uploads to Alibaba Cloud OSS and stores object metadata in the database

## Environment Variables

- `DATABASE_URL`
- `STORAGE_BACKEND`
- `STORAGE_DIR`
- `CORS_ORIGINS`
- `PUBLIC_API_BASE_URL`
- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `OPENAI_BASE_URL`
- `OPENAI_TIMEOUT_SECONDS`
- `RECRUITER_DEFAULT_NAME`
- `OSS_BUCKET`
- `OSS_REGION`
- `OSS_ENDPOINT`
- `OSS_ACCESS_KEY_ID`
- `OSS_ACCESS_KEY_SECRET`
- `OSS_URL_EXPIRES_SECONDS`

## Production Defaults

- PostgreSQL is recommended for `DATABASE_URL`.
- Set `STORAGE_BACKEND=oss` in production.
- Keep `STORAGE_BACKEND=local` only for local development and tests.
- Do not rely on `backend/storage/` for production data persistence.
- If you want real model-driven screening, set `OPENAI_API_KEY` and optionally `OPENAI_BASE_URL`.
- `OPENAI_BASE_URL` can point to an OpenAI-compatible provider endpoint when you are not using the default OpenAI platform URL.
- When the API is unavailable, the service falls back to the built-in heuristic engine instead of failing closed.

## Validation

- Run `pytest -q` inside `backend/` before releasing.
- Verify upload, evaluation, and manual decision endpoints against the target database/storage backend.
