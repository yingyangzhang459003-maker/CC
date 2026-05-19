#!/usr/bin/env bash
set -euo pipefail
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp -n config/config.example.yaml config/config.yaml || true
cp -n .env.example .env || true
python -m src.main init-db --config config/config.yaml
