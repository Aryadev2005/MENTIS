#!/usr/bin/env bash
# MENTIS — Database Setup Script
# Run: chmod +x scripts/setup_db.sh && ./scripts/setup_db.sh

set -euo pipefail

echo "🔷 MENTIS — Database Setup"
echo "================================"

# Load environment
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
  echo "✓ Loaded .env"
fi

# Start Docker services
echo ""
echo "Starting Docker services..."
docker compose up -d postgres redis qdrant

echo ""
echo "Waiting for PostgreSQL to be healthy..."
until docker compose exec postgres pg_isready -U mentis_user -d mentis 2>/dev/null; do
  printf '.'
  sleep 2
done
echo ""
echo "✓ PostgreSQL ready"

echo "Waiting for Redis..."
until docker compose exec redis redis-cli -a "${REDIS_PASSWORD:-mentis_redis_dev}" ping 2>/dev/null | grep -q "PONG"; do
  printf '.'
  sleep 2
done
echo ""
echo "✓ Redis ready"

echo "Waiting for Qdrant..."
until curl -sf "http://localhost:6333/healthz" > /dev/null 2>&1; do
  printf '.'
  sleep 2
done
echo ""
echo "✓ Qdrant ready"

# Set up Python environment
echo ""
echo "Setting up Python environment..."
if [ ! -d "venv" ]; then
  python3.12 -m venv venv
  echo "✓ Created virtualenv"
fi

source venv/bin/activate
pip install -r requirements.txt -q
echo "✓ Python dependencies installed"

# Run Alembic migrations
echo ""
echo "Running database migrations..."
cd api
alembic upgrade head
cd ..
echo "✓ Migrations complete"

# Seed database
echo ""
echo "Seeding company database..."
python scripts/seed_questions.py
echo "✓ Companies seeded"

echo ""
echo "================================"
echo "✅ MENTIS database setup complete!"
echo ""
echo "Next steps:"
echo "  1. Fill in your API keys in .env"
echo "  2. npm install"
echo "  3. npm run dev"
echo ""
echo "🎯 Your unfair advantage is ready."
