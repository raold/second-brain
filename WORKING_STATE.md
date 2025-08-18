# CRITICAL: WORKING STATE DOCUMENTATION
## Date: 2025-08-17 @ 4:22 PM EST
## DO NOT LOSE THIS CONFIGURATION

# ✅ WHAT'S WORKING RIGHT NOW

## 1. Services REQUIRED
- ✅ **PostgreSQL with pgvector** - Port 5432 (Docker)
- ✅ **Second Brain v5.0.0** - Port 8000 (Docker) 
- ✅ **LLaVA v1.6 Mistral 7B** - Port 1234 (http://127.0.0.1:1234)
- ✅ **Google Drive** - Mounted at G:/My Drive/Takeout
- 🔴 **CLIP Service** - REQUIRED at Port 8002 (for embeddings)

## 2. Photo Pipeline Dashboard
- **URL**: http://localhost:8000/api/photo-pipeline/
- **WebSocket**: ws://localhost:8000/api/photo-pipeline/ws
- **Controls**: START/PAUSE/STOP buttons functional
- **Status**: Dashboard loads and connects

## 3. File Locations
- **Google Takeout**: `G:/My Drive/Takeout/`
- **Zip files**: `takeout-20250816T143016Z-1-*.zip` (numbered photo archives)
- **Skip**: `takeout-20250816T143016Z-001.zip` (archive browser, no photos)

## 4. Proven Working Code
```python
# test_photo_pipeline.py WORKS - processes photos with LLaVA
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
TAKEOUT_PATH = "G:/My Drive/Takeout"
LLAVA_SERVICE_URL = "http://127.0.0.1:1234"
# Successfully processes images from zip files
```

# ⚠️ CRITICAL ISSUES TO FIX

## 1. Docker Can't Access G: Drive
**Problem**: Docker container looks for `/takeout` which doesn't exist
**Current State**: Volume mount `"./takeout:/takeout:ro"` doesn't work with G: drive
**Impact**: Pipeline finds 0 files when START clicked

## 2. CLIP Service Dependency
**Problem**: photo_processor.py fails if CLIP service (port 8002) not running
**Error**: `ConnectionRefusedError: Cannot connect to host localhost:8002`
**Impact**: Can't run processor directly without CLIP

## 3. Path Detection Logic
**Current Code** in photo_pipeline.py:
```python
if os.path.exists("/takeout"):  # Docker - NEVER EXISTS
    takeout_path = Path("/takeout")
elif os.path.exists("G:/My Drive/Takeout"):  # Works locally
    takeout_path = Path("G:/My Drive/Takeout")
```

# 🔴 POST-MORTEM: WHY IT BROKE

## Root Causes
1. **Multiple Entry Points**: Had app.py (v4.2.3) and main.py (v5.0.0)
2. **Docker Override**: docker-compose.yml hardcoded `app.app:app` instead of `app.main:app`
3. **Silent Failures**: ImportErrors caught but not surfaced
4. **Path Assumptions**: Docker can't access Windows G: drive
5. **Service Dependencies**: Assumes CLIP service is running

## What Happened After Restart
1. Computer restart → Google Drive unmounted → G: drive gone
2. Docker restarted with wrong entry point (app.app)
3. Photo pipeline routes not registered (weren't in app.py)
4. When fixed, Docker still couldn't see G: drive
5. Direct execution failed due to CLIP dependency

# 🛡️ PERMANENT FIXES IMPLEMENTED

## 1. Single Entry Point
- ✅ Deleted `app.py` completely
- ✅ Only `main.py` exists now
- ✅ Docker configs updated to use `app.main:app`

## 2. Version Management  
- ✅ Single source: `app/__init__.py` has `__version__ = "5.0.0"`
- ✅ All modules import from there

## 3. Technical Debt Documented
- ✅ Created `TECHNICAL_DEBT.md` with all issues
- ✅ Silent failures documented
- ✅ Missing dependencies listed

# 🚨 IMMEDIATE ACTIONS NEEDED

## 1. Make CLIP Optional
```python
# In photo_processor.py
try:
    async with session.get(f"{CLIP_SERVICE_URL}/") as response:
        CLIP_AVAILABLE = response.status == 200
except:
    CLIP_AVAILABLE = False
    print("⚠️ CLIP service not available, using LLaVA only")
```

## 2. Fix Docker Mount for Windows
Option A: Use network path
```yaml
volumes:
  - "//localhost/G$/My Drive/Takeout:/takeout:ro"
```

Option B: Create symlink in project
```bash
mklink /D takeout "G:\My Drive\Takeout"
```

Option C: Run processor outside Docker
```bash
# Don't use Docker for photo processing
python app/services/photo_processor.py
```

## 3. Add Startup Validation
```python
# In factory.py startup
print(f"✅ Photo pipeline path: {takeout_path}")
print(f"✅ Zip files found: {len(zip_files)}")
print(f"✅ LLaVA available: {llava_status}")
print(f"⚠️ CLIP available: {clip_status}")
```

# 📝 STARTUP CHECKLIST

Every time you restart:
1. [ ] Check Google Drive is mounted: `dir G:\`
2. [ ] Start Docker: `docker-compose up -d`
3. [ ] Verify version: `curl http://localhost:8000/` → should show v5.0.0
4. [ ] Check LLaVA: `curl http://127.0.0.1:1234/` → should respond
5. [ ] Open dashboard: http://localhost:8000/api/photo-pipeline/
6. [ ] If needed, start CLIP: `cd services/gpu/clip && python clip_api.py`

# 🔒 NEVER CHANGE THESE

1. **Entry point**: Always `app.main:app`
2. **Version**: Keep in `app/__init__.py` only
3. **Docker command**: Don't override in docker-compose.yml
4. **Path check**: Always log what path is being used

# 💾 COMMIT THIS STATE

```bash
git add -A
git commit -m "WORKING STATE: Photo pipeline functional with LLaVA

- Dashboard: http://localhost:8000/api/photo-pipeline/
- LLaVA: http://127.0.0.1:1234
- Google Takeout: G:/My Drive/Takeout/
- Version: 5.0.0

Critical fixes:
- Single entry point (main.py only)
- Docker uses correct app
- Path detection works locally

Known issues:
- Docker can't mount G: drive
- CLIP service required but not running

DO NOT CHANGE WITHOUT READING WORKING_STATE.md"
```