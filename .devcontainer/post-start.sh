#!/usr/bin/env bash
set -euo pipefail

cd /workspaces/resume-screening-mvp/backend

if [ ! -d .venv ]; then
  python -m venv .venv
fi

. .venv/bin/activate

cat > .env <<EOF
APP_NAME=Resume Screening MVP
DATABASE_URL=sqlite:///./screening.db
STORAGE_BACKEND=local
STORAGE_DIR=storage
CORS_ORIGINS=["http://localhost:3000","http://127.0.0.1:8010","https://niuniu122.github.io"]
OPENAI_API_KEY=${OPENAI_API_KEY:-}
OPENAI_MODEL=${OPENAI_MODEL:-gpt-5.4}
OPENAI_BASE_URL=${OPENAI_BASE_URL:-https://yumi.chat:3000/v1}
OPENAI_TIMEOUT_SECONDS=90
RECRUITER_DEFAULT_NAME=Recruiter
EOF

pkill -f "uvicorn app.main:app --host 0.0.0.0 --port 8010" || true
nohup .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8010 > ../deploy/runtime/backend-codespace.out.log 2> ../deploy/runtime/backend-codespace.err.log < /dev/null &
