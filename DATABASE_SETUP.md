# 🗄️ Database Setup Guide

## PostgreSQL Database Initialization for PROpitashka Bot

This guide will help you set up the PostgreSQL database for the bot.

## Prerequisites

- PostgreSQL 12+ installed
- Access to PostgreSQL with admin privileges

## Quick Start

### 1. Create Database

```bash
# Connect to PostgreSQL as superuser
sudo -u postgres psql

# Create database and user (if needed)
CREATE DATABASE propitashka;
CREATE USER your_username WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE propitashka TO your_username;

# Exit PostgreSQL
\q
```

### 2. Initialize Tables

Run the initialization script:

```bash
psql -U postgres -d propitashka -f database_init.sql
```

Or connect manually:

```bash
psql -U postgres propitashka
\i database_init.sql
```

## Database Structure

### Tables Overview

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `user_lang` | User language preferences | user_id, lang |
| `user_main` | User profile data | user_id, user_name, user_sex |
| `user_health` | Daily health metrics | user_id, date, weight, height, imt |
| `user_aims` | User goals | user_id, user_aim, daily_cal |
| `food` | Food intake log | user_id, date, name_of_food, b, g, u, cal |
| `user_training` | Training sessions | user_id, date, training_cal, tren_time |
| `water` | Water intake tracking | user_id, data, count |
| `bot_logs` | Bot activity logs | timestamp, level, message, user_id |

### Detailed Schema

#### user_lang
```sql
user_id BIGINT PRIMARY KEY
lang VARCHAR(5) -- Language code: ru, en, de, fr, es
created_at TIMESTAMP
updated_at TIMESTAMP
```

#### user_health
```sql
id SERIAL PRIMARY KEY
user_id BIGINT
imt DECIMAL(5,2) -- Body Mass Index
imt_str VARCHAR(100) -- BMI description
cal DECIMAL(7,2) -- Daily calorie target
date DATE
weight DECIMAL(6,2) -- Weight in kg
height DECIMAL(6,2) -- Height in cm
created_at TIMESTAMP
UNIQUE(user_id, date)
```

#### food
```sql
id SERIAL PRIMARY KEY
user_id BIGINT
date DATE
name_of_food VARCHAR(255)
b DECIMAL(8,3) -- Protein (grams)
g DECIMAL(8,3) -- Fat (grams)
u DECIMAL(8,3) -- Carbohydrates (grams)
cal DECIMAL(8,2) -- Calories
created_at TIMESTAMP
```

#### bot_logs
```sql
id SERIAL PRIMARY KEY
timestamp TIMESTAMP
level VARCHAR(10) -- DEBUG, INFO, WARNING, ERROR, CRITICAL
logger_name VARCHAR(100)
message TEXT
user_id BIGINT
username VARCHAR(100)
function_name VARCHAR(100)
line_number INTEGER
error_traceback TEXT
```

## Verify Installation

Check that all tables were created:

```sql
SELECT 
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY tablename;
```

Check indexes:

```sql
SELECT 
    tablename,
    indexname,
    indexdef
FROM pg_indexes 
WHERE schemaname = 'public'
ORDER BY tablename, indexname;
```

## Configuration

Update the `.env` file with your database credentials:

```env
DB_NAME=propitashka
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
```

Or update directly in `main.py`:

```python
conn = psycopg2.connect(
    dbname='propitashka',
    user='postgres',
    password='your_password',
    host='localhost',
    port='5432'
)
```

## Backup and Restore

### Create Backup

```bash
# Full database backup
pg_dump -U postgres propitashka > backup_$(date +%Y%m%d).sql

# Only data (no schema)
pg_dump -U postgres --data-only propitashka > data_backup.sql

# Only specific tables
pg_dump -U postgres -t user_health -t food propitashka > tables_backup.sql
```

### Restore Backup

```bash
# Restore full backup
psql -U postgres propitashka < backup_20250122.sql

# Restore only data
psql -U postgres propitashka < data_backup.sql
```

## Maintenance

### Clean Old Logs

```sql
-- Delete logs older than 90 days
DELETE FROM bot_logs WHERE timestamp < NOW() - INTERVAL '90 days';

-- Keep only last 100,000 records
DELETE FROM bot_logs 
WHERE id NOT IN (
    SELECT id FROM bot_logs 
    ORDER BY timestamp DESC 
    LIMIT 100000
);
```

### Vacuum and Analyze

```sql
-- Optimize database
VACUUM ANALYZE;

-- Detailed vacuum for specific table
VACUUM FULL ANALYZE bot_logs;
```

### Check Database Size

```sql
SELECT 
    pg_database.datname,
    pg_size_pretty(pg_database_size(pg_database.datname)) AS size
FROM pg_database
WHERE datname = 'propitashka';
```

## Troubleshooting

### Connection Error

```
psql: error: connection to server on socket "/var/run/postgresql/.s.PGSQL.5432" failed
```

**Solution:**
```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql

# Start PostgreSQL
sudo systemctl start postgresql

# Enable auto-start
sudo systemctl enable postgresql
```

### Permission Denied

```
ERROR: permission denied for table user_health
```

**Solution:**
```sql
-- Grant all privileges to user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO your_username;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO your_username;
```

### Table Already Exists

```
ERROR: relation "user_health" already exists
```

**Solution:** The script uses `CREATE TABLE IF NOT EXISTS`, so this shouldn't happen. If it does, you can:

1. Drop and recreate:
```sql
DROP TABLE IF EXISTS user_health CASCADE;
-- Then run the init script again
```

2. Or skip table creation and just verify structure matches

## Migration

If you have an existing database, you can migrate data:

```sql
-- Example: Migrate from old structure
INSERT INTO user_health (user_id, weight, height, date)
SELECT user_id, weight, height, created_date
FROM old_user_data;
```

## Performance Tips

1. **Indexes are crucial** - Already created by init script
2. **Regular VACUUM** - Keeps database optimized
3. **Monitor query performance:**

```sql
-- Check slow queries
SELECT 
    query,
    calls,
    total_time,
    mean_time
FROM pg_stat_statements
ORDER BY total_time DESC
LIMIT 10;
```

## Security

1. **Use strong passwords**
2. **Limit network access** in `pg_hba.conf`
3. **Regular backups**
4. **Monitor logs table** - Don't let it grow too large

## Additional Resources

- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [psycopg2 Documentation](https://www.psycopg.org/docs/)
- [SQL Tutorial](https://www.postgresqltutorial.com/)

---

**Need help?** Create an issue on [GitHub](https://github.com/VadimVthvPro/PRO_pitashka/issues)

