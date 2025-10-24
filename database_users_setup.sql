-- ============================================
-- PROpitashka Database Users Setup
-- ============================================
-- This script creates separate database users with appropriate permissions
-- Run as PostgreSQL superuser (postgres)

-- ============================================
-- 1. Create Bot User (Limited Permissions)
-- ============================================
-- Bot user has only necessary permissions for bot operations

-- Drop user if exists (for clean setup)
DROP USER IF EXISTS propitashka_bot;

-- Create bot user
CREATE USER propitashka_bot WITH PASSWORD 'CHANGE_THIS_PASSWORD';

-- Grant connection to database
GRANT CONNECT ON DATABASE propitashka TO propitashka_bot;

-- Grant usage on schema
GRANT USAGE ON SCHEMA public TO propitashka_bot;

-- Grant SELECT, INSERT, UPDATE on all tables (no DELETE for safety)
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO propitashka_bot;

-- Grant usage on sequences (for auto-increment IDs)
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO propitashka_bot;

-- Set default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public 
GRANT SELECT, INSERT, UPDATE ON TABLES TO propitashka_bot;

ALTER DEFAULT PRIVILEGES IN SCHEMA public 
GRANT USAGE, SELECT ON SEQUENCES TO propitashka_bot;

-- ============================================
-- 2. Create Admin User (Full Permissions)
-- ============================================
-- Admin user has full permissions for admin panel

-- Drop user if exists (for clean setup)
DROP USER IF EXISTS propitashka_admin;

-- Create admin user
CREATE USER propitashka_admin WITH PASSWORD 'CHANGE_THIS_ADMIN_PASSWORD';

-- Grant connection to database
GRANT CONNECT ON DATABASE propitashka TO propitashka_admin;

-- Grant all privileges on schema
GRANT ALL PRIVILEGES ON SCHEMA public TO propitashka_admin;

-- Grant all privileges on all tables
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO propitashka_admin;

-- Grant all privileges on sequences
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO propitashka_admin;

-- Set default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public 
GRANT ALL PRIVILEGES ON TABLES TO propitashka_admin;

ALTER DEFAULT PRIVILEGES IN SCHEMA public 
GRANT ALL PRIVILEGES ON SEQUENCES TO propitashka_admin;

-- ============================================
-- 3. Verify Permissions
-- ============================================

-- Check users
\du propitashka_bot
\du propitashka_admin

-- Check table permissions
SELECT grantee, privilege_type 
FROM information_schema.role_table_grants 
WHERE table_schema = 'public' 
  AND grantee IN ('propitashka_bot', 'propitashka_admin')
ORDER BY grantee, table_name, privilege_type;

-- ============================================
-- 4. Security Recommendations
-- ============================================

-- Enable SSL connections (add to postgresql.conf):
-- ssl = on
-- ssl_cert_file = 'server.crt'
-- ssl_key_file = 'server.key'

-- Restrict connections (add to pg_hba.conf):
-- hostssl  propitashka  propitashka_bot     0.0.0.0/0  md5
-- hostssl  propitashka  propitashka_admin   0.0.0.0/0  md5

-- ============================================
-- 5. Usage Instructions
-- ============================================

/*
After running this script:

1. Update .env file:
   DB_USER=propitashka_bot
   DB_PASSWORD=your_bot_password
   ADMIN_DB_USER=propitashka_admin
   ADMIN_DB_PASSWORD=your_admin_password

2. Test bot connection:
   psql -h localhost -U propitashka_bot -d propitashka

3. Test admin connection:
   psql -h localhost -U propitashka_admin -d propitashka

4. Verify bot cannot delete:
   DELETE FROM users WHERE user_id = 1;
   -- Should fail with permission denied

5. Verify admin can delete:
   -- (connect as propitashka_admin)
   DELETE FROM users WHERE user_id = 999999;
   -- Should succeed
*/

-- ============================================
-- 6. Revoke Dangerous Permissions from Bot
-- ============================================

-- Explicitly revoke DELETE and TRUNCATE from bot user
REVOKE DELETE, TRUNCATE ON ALL TABLES IN SCHEMA public FROM propitashka_bot;

-- Revoke DROP permissions
REVOKE DROP ON ALL TABLES IN SCHEMA public FROM propitashka_bot;

-- ============================================
-- Done!
-- ============================================

\echo 'Database users setup completed!'
\echo 'Bot user: propitashka_bot (SELECT, INSERT, UPDATE only)'
\echo 'Admin user: propitashka_admin (ALL PRIVILEGES)'
\echo ''
\echo 'IMPORTANT: Change default passwords in this script before running!'
\echo 'IMPORTANT: Update .env file with new credentials'

