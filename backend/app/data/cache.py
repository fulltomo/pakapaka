import os
import re
import time
import hashlib
from pathlib import Path
from typing import Optional


class HTMLCache:
    """
    Local filesystem cache for HTML pages to avoid repetitive network scraping requests.
    """

    def __init__(
        self,
        cache_dir: Optional[str] = None,
        default_ttl_seconds: Optional[int] = None,
    ):
        if cache_dir is None:
            # Default cache location in backend/cache/html
            base_dir = Path(__file__).resolve().parent.parent.parent
            self.cache_dir = base_dir / "cache" / "html"
        else:
            self.cache_dir = Path(cache_dir)

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.default_ttl_seconds = default_ttl_seconds

    def _key_to_filename(self, key: str) -> str:
        # Safe filename for alphanumeric keys (like race IDs e.g. 202405021211)
        if re.match(r"^[a-zA-Z0-9_\-]+$", key):
            return f"{key}.html"
        # For complex URLs or queries, use sha256 hash prefix + sanitized
        h = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
        safe_prefix = re.sub(r"[^a-zA-Z0-9_\-]", "_", key)[:32]
        return f"{safe_prefix}_{h}.html"

    def _key_to_path(self, key: str) -> Path:
        return self.cache_dir / self._key_to_filename(key)

    def has(self, key: str) -> bool:
        path = self._key_to_path(key)
        if not path.exists():
            return False
        if self.default_ttl_seconds is not None:
            mtime = path.stat().st_mtime
            if (time.time() - mtime) > self.default_ttl_seconds:
                return False
        return True

    def get(self, key: str) -> Optional[str]:
        if not self.has(key):
            return None
        path = self._key_to_path(key)
        try:
            return path.read_text(encoding="utf-8")
        except Exception:
            return None

    def set(self, key: str, content: str) -> None:
        path = self._key_to_path(key)
        # Write to temp file then rename for atomic write
        tmp_path = path.with_suffix(".tmp")
        tmp_path.write_text(content, encoding="utf-8")
        tmp_path.replace(path)

    def delete(self, key: str) -> bool:
        path = self._key_to_path(key)
        if path.exists():
            try:
                path.unlink()
                return True
            except OSError:
                return False
        return False

    def clear(self) -> None:
        for f in self.cache_dir.glob("*.html"):
            try:
                f.unlink()
            except OSError:
                pass
