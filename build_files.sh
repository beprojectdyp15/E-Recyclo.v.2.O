#!/bin/bash
echo "=== E-RECYCLO Vercel Build ==="

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Running database migrations..."
python manage.py migrate --noinput

echo "=== Build complete ==="
