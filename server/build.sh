#!/usr/bin/env bash
set -o errexit

# Upgrade pip, setuptools, and wheel
pip install --upgrade pip setuptools wheel

# Install dependencies without build isolation to avoid Rust compilation issues
PIP_NO_BUILD_ISOLATION=1 pip install -r requirements.txt

# Run Django migrations
python manage.py migrate

