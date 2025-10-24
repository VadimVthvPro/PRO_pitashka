"""
Privacy and Consent Management Module
Handles user consent for privacy policy
"""
import sys
import os
from datetime import datetime
from typing import Optional, Tuple

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import config

# Import database connection
from db_config import get_db_connection, close_db_connection


PRIVACY_POLICY_VERSION = "1.0"
PRIVACY_POLICY_URL = "https://propitashka.github.io/privacy"  # TODO: Update with actual URL


class PrivacyManager:
    """Manages user privacy consent"""
    
    @staticmethod
    def check_consent(user_id: int) -> bool:
        """
        Check if user has given consent to privacy policy
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            True if user has consented, False otherwise
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT consented, revoked 
                FROM privacy_consent 
                WHERE user_id = %s
            """, (user_id,))
            
            result = cursor.fetchone()
            close_db_connection(conn, cursor)
            
            if result:
                consented, revoked = result
                return consented and not revoked
            
            return False
            
        except Exception as e:
            print(f"Error checking consent: {e}")
            return False
    
    @staticmethod
    def record_consent(
        user_id: int,
        consented: bool = True,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """
        Record user's consent to privacy policy
        
        Args:
            user_id: Telegram user ID
            consented: Whether user consented
            ip_address: User's IP address (optional)
            user_agent: User's user agent (optional)
            
        Returns:
            True if recorded successfully, False otherwise
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Check if record exists
            cursor.execute("""
                SELECT consent_id FROM privacy_consent WHERE user_id = %s
            """, (user_id,))
            
            exists = cursor.fetchone()
            
            if exists:
                # Update existing record
                cursor.execute("""
                    UPDATE privacy_consent
                    SET consented = %s,
                        consent_date = %s,
                        consent_version = %s,
                        ip_address = %s,
                        user_agent = %s,
                        revoked = FALSE,
                        revoke_date = NULL
                    WHERE user_id = %s
                """, (
                    consented,
                    datetime.now() if consented else None,
                    PRIVACY_POLICY_VERSION,
                    ip_address,
                    user_agent,
                    user_id
                ))
            else:
                # Insert new record
                cursor.execute("""
                    INSERT INTO privacy_consent 
                    (user_id, consented, consent_date, consent_version, ip_address, user_agent)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    user_id,
                    consented,
                    datetime.now() if consented else None,
                    PRIVACY_POLICY_VERSION,
                    ip_address,
                    user_agent
                ))
            
            # Also update users table
            if consented:
                cursor.execute("""
                    UPDATE users
                    SET privacy_accepted = TRUE,
                        privacy_accepted_at = %s
                    WHERE user_id = %s
                """, (datetime.now(), user_id))
            
            conn.commit()
            close_db_connection(conn, cursor)
            
            return True
            
        except Exception as e:
            print(f"Error recording consent: {e}")
            return False
    
    @staticmethod
    def revoke_consent(user_id: int) -> bool:
        """
        Revoke user's consent
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            True if revoked successfully, False otherwise
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE privacy_consent
                SET revoked = TRUE,
                    revoke_date = %s
                WHERE user_id = %s
            """, (datetime.now(), user_id))
            
            # Update users table
            cursor.execute("""
                UPDATE users
                SET privacy_accepted = FALSE
                WHERE user_id = %s
            """, (user_id,))
            
            conn.commit()
            close_db_connection(conn, cursor)
            
            return True
            
        except Exception as e:
            print(f"Error revoking consent: {e}")
            return False
    
    @staticmethod
    def get_consent_info(user_id: int) -> Optional[dict]:
        """
        Get detailed consent information for user
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Dictionary with consent information or None
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    consented,
                    consent_date,
                    consent_version,
                    revoked,
                    revoke_date,
                    created_at
                FROM privacy_consent
                WHERE user_id = %s
            """, (user_id,))
            
            result = cursor.fetchone()
            close_db_connection(conn, cursor)
            
            if result:
                return {
                    'consented': result[0],
                    'consent_date': result[1],
                    'consent_version': result[2],
                    'revoked': result[3],
                    'revoke_date': result[4],
                    'created_at': result[5]
                }
            
            return None
            
        except Exception as e:
            print(f"Error getting consent info: {e}")
            return None
    
    @staticmethod
    def get_consent_stats() -> dict:
        """
        Get statistics about consent
        
        Returns:
            Dictionary with consent statistics
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Total users
            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0]
            
            # Users who consented
            cursor.execute("""
                SELECT COUNT(*) FROM privacy_consent 
                WHERE consented = TRUE AND revoked = FALSE
            """)
            consented_users = cursor.fetchone()[0]
            
            # Users who revoked
            cursor.execute("""
                SELECT COUNT(*) FROM privacy_consent 
                WHERE revoked = TRUE
            """)
            revoked_users = cursor.fetchone()[0]
            
            # Users without consent record
            cursor.execute("""
                SELECT COUNT(*) FROM users 
                WHERE user_id NOT IN (SELECT user_id FROM privacy_consent)
            """)
            no_record_users = cursor.fetchone()[0]
            
            close_db_connection(conn, cursor)
            
            return {
                'total_users': total_users,
                'consented': consented_users,
                'revoked': revoked_users,
                'no_record': no_record_users,
                'consent_rate': (consented_users / total_users * 100) if total_users > 0 else 0
            }
            
        except Exception as e:
            print(f"Error getting consent stats: {e}")
            return {}


def require_consent(func):
    """
    Decorator to require privacy consent before executing function
    
    Usage:
        @require_consent
        async def some_handler(message: Message):
            ...
    """
    async def wrapper(message, *args, **kwargs):
        user_id = message.from_user.id
        
        if not PrivacyManager.check_consent(user_id):
            await message.answer(
                "⚠️ Для использования бота необходимо принять политику конфиденциальности.\n"
                "Используйте команду /start для начала работы."
            )
            return
        
        return await func(message, *args, **kwargs)
    
    return wrapper


# Singleton instance
privacy_manager = PrivacyManager()

