#!/usr/bin/env bash
# build.sh — Render build script
# Installs Python dependencies and downloads NLTK tokenizer data

set -e

echo "=== Installing Python dependencies ==="
pip install -r requirements.txt

echo "=== Downloading NLTK data ==="
python nltk_setup.py

echo "=== Build complete ==="
