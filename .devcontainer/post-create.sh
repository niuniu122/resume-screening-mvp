#!/usr/bin/env bash
set -euo pipefail

cd /workspaces/resume-screening-mvp/backend
python -m pip install --upgrade pip
pip install -r requirements.txt
