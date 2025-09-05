#!/usr/bin/env bash
set -e
python ./model/download_haarcascade.py
uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}
