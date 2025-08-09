# Starting PostgreSQL for Second Brain v4.2.0

## Option 1: Docker Desktop on Windows (Recommended)

Since you're on Windows 11 with WSL2, open PowerShell or Command Prompt **on Windows** (not in WSL2) and run:

```powershell
# From Windows PowerShell/CMD
cd C:\tools\second-brain
docker-compose up -d postgres adminer
```

This will start:
- PostgreSQL 16 with pgvector extension on port 5432
- Adminer (database UI) on port 8080

## Option 2: Docker in WSL2

If Docker Desktop has WSL2 integration enabled:

1. Check Docker Desktop settings → Resources → WSL Integration
2. Enable integration with your WSL2 distro
3. Restart Docker Desktop
4. In WSL2, run:
   ```bash
   cd /mnt/c/tools/second-brain
   docker-compose up -d postgres adminer
   ```

## Option 3: Direct PostgreSQL Installation (Without Docker)

If Docker isn't working, install PostgreSQL directly in WSL2:

```bash
# Install PostgreSQL 16 with pgvector
sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
sudo apt update
sudo apt install postgresql-16 postgresql-16-pgvector

# Start PostgreSQL
sudo service postgresql start

# Create database and user
sudo -u postgres psql <<EOF
CREATE USER secondbrain WITH PASSWORD 'changeme';
CREATE DATABASE secondbrain OWNER secondbrain;
\c secondbrain
CREATE EXTENSION IF NOT EXISTS vector;
EOF
```

## Verify Connection

Once PostgreSQL is running, test the connection:

```bash
# From WSL2
psql -h localhost -U secondbrain -d secondbrain -c "SELECT version();"
```

Or use the Python script:
```bash
.venv/bin/python -c "
import asyncpg
import asyncio

async def test():
    conn = await asyncpg.connect('postgresql://secondbrain:changeme@localhost/secondbrain')
    version = await conn.fetchval('SELECT version()')
    print(f'✅ Connected to: {version}')
    await conn.close()

asyncio.run(test())
"
```

## Database Schema

Once connected, the app will auto-create tables on first run, or manually initialize:

```bash
.venv/bin/python scripts/setup_postgres_pgvector.py
```

## Access Database UI

- **Adminer**: http://localhost:8080
  - Server: `postgres` (if using Docker) or `localhost` (if local)
  - Username: `secondbrain`
  - Password: `changeme`
  - Database: `secondbrain`

## Environment Variables

Your `.env` is already configured correctly:
```
DATABASE_URL=postgresql://secondbrain:changeme@localhost:5432/secondbrain
```

## Start the Backend

Once PostgreSQL is running:

```bash
# Kill any existing backend
pkill -f uvicorn

# Start the real backend (not the mock)
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The backend will:
1. Connect to PostgreSQL
2. Create tables if they don't exist
3. Enable pgvector for semantic search
4. Serve the API on http://localhost:8000