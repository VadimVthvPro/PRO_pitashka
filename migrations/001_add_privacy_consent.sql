-- ============================================
-- Migration: Add Privacy Consent System
-- Version: 001
-- Date: 2025-10-24
-- ============================================

-- Create privacy_consent table
CREATE TABLE IF NOT EXISTS privacy_consent (
    consent_id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL UNIQUE,
    consented BOOLEAN NOT NULL DEFAULT FALSE,
    consent_date TIMESTAMP,
    consent_version VARCHAR(10) DEFAULT '1.0',
    ip_address VARCHAR(45),
    user_agent TEXT,
    revoked BOOLEAN DEFAULT FALSE,
    revoke_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign key to users table
    CONSTRAINT fk_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE CASCADE
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_privacy_consent_user_id 
ON privacy_consent(user_id);

CREATE INDEX IF NOT EXISTS idx_privacy_consent_consented 
ON privacy_consent(consented);

-- Create trigger to update updated_at
CREATE OR REPLACE FUNCTION update_privacy_consent_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_privacy_consent_timestamp
    BEFORE UPDATE ON privacy_consent
    FOR EACH ROW
    EXECUTE FUNCTION update_privacy_consent_timestamp();

-- Add privacy_url column to users table (optional)
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS privacy_accepted BOOLEAN DEFAULT FALSE;

ALTER TABLE users 
ADD COLUMN IF NOT EXISTS privacy_accepted_at TIMESTAMP;

-- Comments for documentation
COMMENT ON TABLE privacy_consent IS 'Stores user consent for privacy policy';
COMMENT ON COLUMN privacy_consent.consent_version IS 'Version of privacy policy accepted';
COMMENT ON COLUMN privacy_consent.revoked IS 'TRUE if user revoked consent';

-- Grant permissions to bot user
GRANT SELECT, INSERT, UPDATE ON privacy_consent TO propitashka_bot;
GRANT USAGE, SELECT ON SEQUENCE privacy_consent_consent_id_seq TO propitashka_bot;

-- Grant full permissions to admin user
GRANT ALL PRIVILEGES ON privacy_consent TO propitashka_admin;
GRANT ALL PRIVILEGES ON SEQUENCE privacy_consent_consent_id_seq TO propitashka_admin;

-- ============================================
-- Rollback Script (if needed)
-- ============================================
/*
DROP TRIGGER IF EXISTS trigger_update_privacy_consent_timestamp ON privacy_consent;
DROP FUNCTION IF EXISTS update_privacy_consent_timestamp();
DROP TABLE IF NOT EXISTS privacy_consent CASCADE;
ALTER TABLE users DROP COLUMN IF EXISTS privacy_accepted;
ALTER TABLE users DROP COLUMN IF EXISTS privacy_accepted_at;
*/

-- ============================================
-- Verification
-- ============================================
SELECT 'Migration 001 completed successfully!' AS status;
\d privacy_consent

