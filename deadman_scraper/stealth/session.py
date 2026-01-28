"""
Session and Cookie Extraction
=============================
Extract authenticated sessions from Chrome for session replication.
Linux-focused implementation.
"""

import base64
import json
import logging
import os
import shutil
import sqlite3
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


class SessionStealer:
    """
    Extracts authenticated sessions from Chrome browser.
    Uses user's own cookies - requires Chrome to be installed.
    """

    def __init__(self):
        self.chrome_path = self._get_chrome_path()
        self.encryption_key = None

    def _get_chrome_path(self) -> Path:
        """Get Chrome data path (Linux/macOS)."""
        # Check for Chrome
        chrome_path = Path.home() / ".config" / "google-chrome"
        if chrome_path.exists():
            return chrome_path

        # Check for Chromium
        chromium_path = Path.home() / ".config" / "chromium"
        if chromium_path.exists():
            return chromium_path

        # macOS fallback
        mac_path = Path.home() / "Library" / "Application Support" / "Google" / "Chrome"
        if mac_path.exists():
            return mac_path

        # Default to Chrome path even if not found
        return chrome_path

    def _get_encryption_key(self) -> bytes | None:
        """Get Chrome's encryption key from Local State."""
        local_state_path = self.chrome_path / "Local State"
        if not local_state_path.exists():
            logger.debug(f"Local State not found at {local_state_path}")
            return None

        try:
            with open(local_state_path, encoding='utf-8') as f:
                local_state = json.load(f)

            encrypted_key = base64.b64decode(
                local_state['os_crypt']['encrypted_key']
            )[5:]  # Strip 'DPAPI' prefix

            # On Linux, Chrome uses libsecret/gnome-keyring
            # The key extraction is simpler - it's stored directly
            return encrypted_key

        except KeyError:
            logger.debug("No os_crypt key found - cookies may be unencrypted")
            return None
        except Exception as e:
            logger.error(f"Encryption key recovery failed: {e}")
            return None

    def _decrypt_value(self, ciphertext: bytes, key: bytes) -> str | None:
        """Decrypt AES-GCM encrypted cookie values."""
        if not ciphertext:
            return None

        # v10/v11 prefix indicates encrypted cookie
        if ciphertext[:3] not in (b'v10', b'v11'):
            # Unencrypted value
            try:
                return ciphertext.decode('utf-8')
            except Exception:
                return None

        try:
            from Crypto.Cipher import AES

            nonce = ciphertext[3:15]
            payload = ciphertext[15:]
            cipher = AES.new(key, AES.MODE_GCM, nonce)
            return cipher.decrypt(payload)[:-16].decode('utf-8')
        except ImportError:
            logger.warning("pycryptodome not installed - cannot decrypt cookies")
            return None
        except Exception as e:
            logger.debug(f"Decryption failed: {e}")
            return None

    def steal_cookies(self, domain: str) -> dict[str, str]:
        """
        Extract cookies for a specific domain.

        Args:
            domain: Domain to extract cookies for (e.g., 'reddit.com')

        Returns:
            Dictionary of cookie name -> value
        """
        # Try multiple cookie database locations
        cookie_paths = [
            self.chrome_path / "Default" / "Network" / "Cookies",
            self.chrome_path / "Default" / "Cookies",
        ]

        cookies_db = None
        for path in cookie_paths:
            if path.exists():
                cookies_db = path
                break

        if not cookies_db:
            logger.warning(f"Chrome cookie database not found in {self.chrome_path}")
            return {}

        # Copy database to avoid locking issues
        temp_db = Path(tempfile.gettempdir()) / "deadman_cookies_copy.db"
        try:
            shutil.copy2(str(cookies_db), str(temp_db))
        except Exception as e:
            logger.error(f"Failed to copy cookie database: {e}")
            return {}

        cookies = {}
        try:
            key = self._get_encryption_key()

            conn = sqlite3.connect(str(temp_db))
            cursor = conn.cursor()

            # Query cookies for domain
            cursor.execute(
                "SELECT name, encrypted_value, value FROM cookies WHERE host_key LIKE ?",
                (f"%{domain}%",)
            )

            for name, enc_val, plain_val in cursor.fetchall():
                # Try encrypted value first
                if enc_val and key:
                    dec_val = self._decrypt_value(enc_val, key)
                    if dec_val:
                        cookies[name] = dec_val
                        continue

                # Fall back to plain value
                if plain_val:
                    cookies[name] = plain_val

            conn.close()

            if cookies:
                logger.info(f"Extracted {len(cookies)} cookies for {domain}")
            else:
                logger.debug(f"No cookies found for {domain}")

            return cookies

        except Exception as e:
            logger.error(f"Cookie extraction failed: {e}")
            return {}

        finally:
            if temp_db.exists():
                os.remove(temp_db)

    def get_session_cookies(self, domain: str) -> str | None:
        """
        Get cookies formatted as a Cookie header value.

        Args:
            domain: Domain to get cookies for

        Returns:
            Cookie header string or None
        """
        cookies = self.steal_cookies(domain)
        if not cookies:
            return None

        return "; ".join(f"{k}={v}" for k, v in cookies.items())
