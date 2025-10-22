# 🔄 Database Migration Guide

## Centralized PostgreSQL Configuration

The bot now uses a **single centralized PostgreSQL database** for all operations.

## What Changed

### ❌ Before (Multiple connections)
```python
# In main.py
conn = psycopg2.connect(dbname='propitashka', user='postgres', ...)

# In logger_config.py
db_config = {'dbname': 'propitashka', 'user': 'postgres', ...}
```

### ✅ After (Single configuration)
```python
# All modules now use db_config.py
from db_config import conn, cursor, DB_CONFIG
```

## Benefits

1. **Single source of truth** - All database credentials in one place
2. **Environment variables support** - Use `.env` for configuration
3. **Easier maintenance** - Change connection settings in one file
4. **No SQLite** - Only PostgreSQL is used
5. **Better error handling** - Centralized connection management

## Configuration

### Option 1: Using .env (Recommended)

Create `.env` file:
```env
DB_NAME=propitashka
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
```

### Option 2: Default values

If `.env` is not provided, defaults are used:
- DB_NAME: propitashka
- DB_USER: postgres
- DB_PASSWORD: vadamahjkl
- DB_HOST: localhost
- DB_PORT: 5432

## Files Modified

1. **`PROpitashka/db_config.py`** ✨ NEW
   - Centralized database configuration
   - Connection pooling
   - Helper functions

2. **`PROpitashka/main.py`** ✅ Updated
   - Imports connection from `db_config`
   - Removed hardcoded credentials

3. **`PROpitashka/logger_config.py`** ✅ Updated
   - Uses `DB_CONFIG` from centralized module
   - Same PostgreSQL database for logs

4. **`.gitignore`** ✅ Updated
   - Added `*.sql.backup` and `*.dump`
   - Kept SQLite ignore rules (legacy)

5. **`README.md`** ✅ Updated
   - Added database configuration in `.env` section

## Removed Files

- ❌ `PROpitashka/pro3.db` - SQLite database (not used)

## Migration Steps

If you're updating from an older version:

### Step 1: Backup your data
```bash
pg_dump -U postgres propitashka > backup_before_migration.sql
```

### Step 2: Update code
```bash
git pull origin main
```

### Step 3: Configure .env
```bash
cp .env.example .env
# Edit .env with your database credentials
```

### Step 4: Restart bot
```bash
cd PROpitashka
python main.py
```

## Troubleshooting

### Connection Error
```
Error connecting to database: password authentication failed
```

**Solution:** Check your `.env` file has correct `DB_PASSWORD`

### Module Import Error
```
ModuleNotFoundError: No module named 'db_config'
```

**Solution:** Make sure you're running bot from correct directory:
```bash
cd PROpitashka  # Must be in this directory
python main.py
```

### Logger Cannot Connect to DB
```
Failed to connect DatabaseHandler: ...
```

**Solution:** 
1. Verify PostgreSQL is running: `sudo systemctl status postgresql`
2. Check database exists: `psql -U postgres -l | grep propitashka`
3. Run initialization script: `psql -U postgres -d propitashka -f database_init.sql`

## Database Connection Details

### Global Connection
```python
# In db_config.py
conn = get_db_connection()  # Single persistent connection
cursor = conn.cursor()       # Global cursor
```

This connection is imported by:
- `main.py` - Bot operations
- `logger_config.py` - Log storage

### Helper Functions
```python
# Create new connection
conn = get_db_connection()

# Get cursor
conn, cursor = get_db_cursor()

# Close safely
close_db_connection(conn, cursor)
```

## Performance Notes

- **Single connection** is used for bot operations (better for concurrent access)
- **Separate connections** created by logger as needed
- Connection is **persistent** and reused
- **Auto-reconnect** on connection loss (handled by psycopg2)

## Security Checklist

- ✅ Database credentials in `.env` (not in code)
- ✅ `.env` is in `.gitignore`
- ✅ SQLite removed (no local db files)
- ✅ PostgreSQL only (production-ready)
- ✅ Connection pooling available if needed

## Future Improvements

Consider these enhancements:

1. **Connection Pooling**
```python
from psycopg2 import pool
connection_pool = pool.SimpleConnectionPool(1, 20, **DB_CONFIG)
```

2. **Async Support**
```python
import asyncpg
conn = await asyncpg.connect(**DB_CONFIG)
```

3. **ORM Integration**
```python
from sqlalchemy import create_engine
engine = create_engine(f"postgresql://{user}:{password}@{host}/{dbname}")
```

## Questions?

- 📖 See [DATABASE_SETUP.md](DATABASE_SETUP.md) for initial setup
- 📊 See [LOGGING.md](LOGGING.md) for log configuration
- 🐛 Create issue on [GitHub](https://github.com/VadimVthvPro/PRO_pitashka/issues)

---

**Status**: ✅ Migration Complete - All modules now use PostgreSQL exclusively

