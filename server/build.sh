#!/usr/bin/env bash
set -o errexit

# Upgrade pip and build tools
pip install --upgrade pip setuptools wheel

# Install dependencies with --no-build-isolation to avoid read-only filesystem issues
pip install --no-build-isolation -r requirements.txt

# Run Django migrations
python manage.py migrate
