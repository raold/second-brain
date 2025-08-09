# 🚀 START THE REAL SECOND BRAIN

## Step 1: Start PostgreSQL (FROM WINDOWS)

Open **PowerShell** or **Command Prompt** on Windows (NOT WSL2) and run:

```powershell
cd C:\tools\second-brain
docker-compose up -d postgres
```

Wait for it to say "Container secondbrain-postgres Started"

## Step 2: Return to WSL2 Terminal

Back in your WSL2 terminal, run:

```bash
cd /mnt/c/tools/second-brain
./start_backend.sh
```

## Step 3: Open the Dashboard

Open your browser to:
- **API Docs**: http://localhost:8000/docs
- **Dashboard**: file:///C:/tools/second-brain/dashboard.html

## What You'll Get:

✅ **REAL PostgreSQL Database** - Data persists forever
✅ **OpenAI Embeddings** - Automatic vector generation  
✅ **Semantic Search** - Find related memories with AI
✅ **Full-Text Search** - PostgreSQL's powerful search
✅ **Production Architecture** - The actual v4.2.0 system

## Troubleshooting:

If PostgreSQL won't start:
- Make sure Docker Desktop is running on Windows
- Check Docker Desktop → Settings → Resources → WSL Integration
- Enable integration with your WSL2 distro

If the backend won't connect:
- Wait 10 seconds after starting PostgreSQL
- Check `.env` has correct database settings
- Try: `docker ps` from Windows to verify container is running

## Success Indicators:

When everything is working, you'll see:
1. PostgreSQL container running in Docker Desktop
2. Backend shows "Application startup complete"
3. API docs at http://localhost:8000/docs work
4. Creating a memory actually persists (survives restart!)

---

**This is the REAL system - not a demo!**