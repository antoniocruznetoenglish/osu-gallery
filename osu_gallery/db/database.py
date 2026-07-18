"""SQLite database layer for osu gallery.

Provides CRUD operations for patterns and tags, with many-to-many
relationship management via the PatternTag junction table.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from osu_gallery.db.models import Pattern, Tag

logger = logging.getLogger(__name__)


def get_data_dir() -> Path:
    """Return the data directory for the application.

    In a PyInstaller-frozen app, uses the executable's directory.
    In development, uses the project root (parent of the package).
    """
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).parent
    else:
        base = Path(__file__).parent.parent.parent
    data_dir = base / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def set_search_engine(search_engine: object) -> None:
    """Set the SearchEngine instance for FTS5 sync callbacks.

    This is a module-level reference so database operations can notify
    the search engine to keep the FTS5 index in sync.
    """
    global _search_engine
    _search_engine = search_engine


_search_engine: object | None = None


class DatabaseError(Exception):
    """Raised when a database operation fails."""


class GalleryDatabase:
    """Manages the SQLite database for the osu gallery."""

    def __init__(self, db_path: str | Path) -> None:
        """Open a connection to the SQLite database at db_path.

        Args:
            db_path: Path to the SQLite database file. The parent
                directory is created if it does not exist.
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None

    @property
    def conn(self) -> sqlite3.Connection:
        """Return the SQLite connection, creating it on first access.

        The connection is configured with WAL journal mode and foreign
        key enforcement. The database schema is created or migrated
        lazily on first access.

        Returns:
            An active sqlite3.Connection.

        Raises:
            DatabaseError: If the connection or schema initialization fails.
        """
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
            self._init_schema()
        return self._conn

    def close(self) -> None:
        """Close the underlying SQLite connection if open."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def _init_schema(self) -> None:
        """Create tables if they don't exist, and migrate existing tables."""
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS tag (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                category TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS pattern (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                raw_code TEXT NOT NULL,
                objects_only TEXT NOT NULL DEFAULT '',
                object_count INTEGER NOT NULL DEFAULT 0,
                circle_count INTEGER NOT NULL DEFAULT 0,
                slider_count INTEGER NOT NULL DEFAULT 0,
                timing_bpm REAL NOT NULL DEFAULT 0.0,
                timing_bpm_min REAL NOT NULL DEFAULT 0.0,
                timing_bpm_max REAL NOT NULL DEFAULT 0.0,
                artist TEXT NOT NULL DEFAULT '',
                title TEXT NOT NULL DEFAULT '',
                mapper TEXT NOT NULL DEFAULT '',
                mapping_tags TEXT NOT NULL DEFAULT '',
                user_image BLOB,
                user_image_preview BLOB,
                user_image_filename TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS pattern_tag (
                pattern_id INTEGER NOT NULL REFERENCES pattern(id) ON DELETE CASCADE,
                tag_id INTEGER NOT NULL REFERENCES tag(id) ON DELETE CASCADE,
                PRIMARY KEY (pattern_id, tag_id)
            );

            CREATE INDEX IF NOT EXISTS idx_pattern_tag_tag_id
                ON pattern_tag(tag_id);

            CREATE INDEX IF NOT EXISTS idx_pattern_tag_pattern_id
                ON pattern_tag(pattern_id);

            CREATE TABLE IF NOT EXISTS custom_mapping_tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tag_name TEXT NOT NULL UNIQUE,
                enabled INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        self._migrate_existing_schema()

    def _column_exists(self, table: str, column: str) -> bool:
        """Check if a column exists in a table."""
        columns = self.conn.execute(f"PRAGMA table_info({table})").fetchall()
        return any(col["name"] == column for col in columns)

    def _migrate_existing_schema(self) -> None:
        """Add new columns to existing tables for backward compatibility."""
        if not self._column_exists("pattern", "circle_count"):
            self.conn.execute(
                "ALTER TABLE pattern ADD COLUMN circle_count INTEGER NOT NULL DEFAULT 0"
            )
        if not self._column_exists("pattern", "slider_count"):
            self.conn.execute(
                "ALTER TABLE pattern ADD COLUMN slider_count INTEGER NOT NULL DEFAULT 0"
            )
        if not self._column_exists("pattern", "objects_only"):
            self.conn.execute(
                "ALTER TABLE pattern ADD COLUMN objects_only TEXT NOT NULL DEFAULT ''"
            )
        if not self._column_exists("pattern", "artist"):
            self.conn.execute(
                "ALTER TABLE pattern ADD COLUMN artist TEXT NOT NULL DEFAULT ''"
            )
        if not self._column_exists("pattern", "title"):
            self.conn.execute(
                "ALTER TABLE pattern ADD COLUMN title TEXT NOT NULL DEFAULT ''"
            )
        if not self._column_exists("pattern", "mapper"):
            self.conn.execute(
                "ALTER TABLE pattern ADD COLUMN mapper TEXT NOT NULL DEFAULT ''"
            )
        if not self._column_exists("pattern", "mapping_tags"):
            self.conn.execute(
                "ALTER TABLE pattern ADD COLUMN mapping_tags TEXT NOT NULL DEFAULT ''"
            )
        if not self._column_exists("pattern", "user_image"):
            self.conn.execute(
                "ALTER TABLE pattern ADD COLUMN user_image BLOB"
            )
        if not self._column_exists("pattern", "user_image_filename"):
            self.conn.execute(
                "ALTER TABLE pattern ADD COLUMN user_image_filename TEXT NOT NULL DEFAULT ''"
            )
        if not self._column_exists("pattern", "timing_bpm_min"):
            self.conn.execute(
                "ALTER TABLE pattern ADD COLUMN timing_bpm_min REAL NOT NULL DEFAULT 0.0"
            )
        if not self._column_exists("pattern", "timing_bpm_max"):
            self.conn.execute(
                "ALTER TABLE pattern ADD COLUMN timing_bpm_max REAL NOT NULL DEFAULT 0.0"
            )
        if not self._column_exists("pattern", "user_image_preview"):
            self.conn.execute(
                "ALTER TABLE pattern ADD COLUMN user_image_preview BLOB"
            )

    # -- Tag CRUD --

    def create_tag(self, name: str, category: str = "") -> Tag:
        """Insert a new tag and return it with its assigned id."""
        tag = Tag(name=name, category=category)
        try:
            cursor = self.conn.execute(
                "INSERT INTO tag (name, category) VALUES (?, ?)",
                (tag.name, tag.category),
            )
        except sqlite3.IntegrityError as err:
            raise DatabaseError(f"Tag with name '{name}' already exists") from err
        tag.id = cursor.lastrowid
        self.conn.commit()
        self._notify_search_sync()
        return tag

    def get_tag(self, tag_id: int) -> Tag | None:
        """Return a tag by id, or None if not found."""
        row = self.conn.execute(
            "SELECT id, name, category FROM tag WHERE id = ?", (tag_id,)
        ).fetchone()
        if row is None:
            return None
        return Tag(id=row["id"], name=row["name"], category=row["category"])

    def get_tag_by_name(self, name: str) -> Tag | None:
        """Return a tag by name, or None if not found."""
        row = self.conn.execute(
            "SELECT id, name, category FROM tag WHERE name = ?", (name,)
        ).fetchone()
        if row is None:
            return None
        return Tag(id=row["id"], name=row["name"], category=row["category"])

    def get_all_tags(self) -> list[Tag]:
        """Return all tags."""
        rows = self.conn.execute(
            "SELECT id, name, category FROM tag ORDER BY name"
        ).fetchall()
        return [Tag(id=r["id"], name=r["name"], category=r["category"]) for r in rows]

    def update_tag(self, tag: Tag) -> None:
        """Update an existing tag's name and/or category."""
        self.conn.execute(
            "UPDATE tag SET name = ?, category = ? WHERE id = ?",
            (tag.name, tag.category, tag.id),
        )
        self.conn.commit()
        self._notify_search_sync()

    def delete_tag(self, tag_id: int) -> None:
        """Delete a tag by id. Related pattern_tag entries are removed via CASCADE."""
        self.conn.execute("DELETE FROM tag WHERE id = ?", (tag_id,))
        self.conn.commit()
        self._notify_search_sync()

    # -- Pattern CRUD --

    def create_pattern(
        self,
        raw_code: str,
        objects_only: str = "",
        object_count: int = 0,
        circle_count: int = 0,
        slider_count: int = 0,
        timing_bpm: float = 0.0,
        timing_bpm_min: float = 0.0,
        timing_bpm_max: float = 0.0,
        artist: str = "",
        title: str = "",
        mapper: str = "",
        mapping_tags: str = "",
        user_image: bytes = b"",
        user_image_preview: bytes = b"",
        user_image_filename: str = "",
    ) -> Pattern:
        """Insert a new pattern and return it with its assigned id."""
        now = datetime.now(timezone.utc).isoformat()
        cursor = self.conn.execute(
            "INSERT INTO pattern "
            "(created_at, updated_at, raw_code, objects_only, object_count, "
            "circle_count, slider_count, timing_bpm, timing_bpm_min, timing_bpm_max, "
            "artist, title, mapper, mapping_tags, "
            "user_image, user_image_preview, user_image_filename) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                now, now, raw_code, objects_only,
                object_count, circle_count, slider_count, timing_bpm,
                timing_bpm_min, timing_bpm_max,
                artist, title, mapper, mapping_tags,
                user_image, user_image_preview, user_image_filename,
            ),
        )
        self.conn.commit()
        self._notify_search_sync(pattern_id=cursor.lastrowid)
        return Pattern(
            id=cursor.lastrowid,
            created_at=datetime.fromisoformat(now),
            updated_at=datetime.fromisoformat(now),
            raw_code=raw_code,
            objects_only=objects_only,
            object_count=object_count,
            circle_count=circle_count,
            slider_count=slider_count,
            timing_bpm=timing_bpm,
            timing_bpm_min=timing_bpm_min,
            timing_bpm_max=timing_bpm_max,
            artist=artist,
            title=title,
            mapper=mapper,
            mapping_tags=json.loads(mapping_tags) if mapping_tags else [],
            user_image=user_image,
            user_image_preview=user_image_preview,
            user_image_filename=user_image_filename,
        )

    def get_pattern(self, pattern_id: int) -> Pattern | None:
        """Return a pattern by id, or None if not found."""
        row = self.conn.execute(
            "SELECT id, created_at, updated_at, raw_code, objects_only, "
            "object_count, circle_count, slider_count, timing_bpm, timing_bpm_min, timing_bpm_max, "
            "artist, title, mapper, mapping_tags, "
            "user_image, user_image_preview, user_image_filename "
            "FROM pattern WHERE id = ?",
            (pattern_id,),
        ).fetchone()
        if row is None:
            return None
        return Pattern(
            id=row["id"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            raw_code=row["raw_code"],
            objects_only=row["objects_only"],
            object_count=row["object_count"],
            circle_count=row["circle_count"],
            slider_count=row["slider_count"],
            timing_bpm=row["timing_bpm"],
            timing_bpm_min=row["timing_bpm_min"],
            timing_bpm_max=row["timing_bpm_max"],
            artist=row["artist"],
            title=row["title"],
            mapper=row["mapper"],
            mapping_tags=json.loads(row["mapping_tags"]) if row["mapping_tags"] else [],
            tag_ids=self._get_pattern_tag_ids(row["id"]),
            user_image=row["user_image"] if row["user_image"] is not None else b"",
            user_image_preview=(
                row["user_image_preview"] if row["user_image_preview"] is not None else b""
            ),
            user_image_filename=row["user_image_filename"] or "",
        )

    def get_all_patterns(self) -> list[Pattern]:
        """Return all patterns ordered by created_at descending."""
        rows = self.conn.execute(
            "SELECT id, created_at, updated_at, raw_code, objects_only, "
            "object_count, circle_count, slider_count, timing_bpm, timing_bpm_min, timing_bpm_max, "
            "artist, title, mapper, mapping_tags, "
            "user_image, user_image_preview, user_image_filename "
            "FROM pattern ORDER BY created_at DESC"
        ).fetchall()
        patterns: list[Pattern] = []
        for row in rows:
            p = Pattern(
                id=row["id"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
                raw_code=row["raw_code"],
                objects_only=row["objects_only"],
                object_count=row["object_count"],
                circle_count=row["circle_count"],
                slider_count=row["slider_count"],
                timing_bpm=row["timing_bpm"],
                timing_bpm_min=row["timing_bpm_min"],
                timing_bpm_max=row["timing_bpm_max"],
                artist=row["artist"],
                title=row["title"],
                mapper=row["mapper"],
                mapping_tags=json.loads(row["mapping_tags"]) if row["mapping_tags"] else [],
                user_image=row["user_image"] if row["user_image"] is not None else b"",
                user_image_preview=(
                    row["user_image_preview"] if row["user_image_preview"] is not None else b""
                ),
                user_image_filename=row["user_image_filename"] or "",
            )
            p.tag_ids = self._get_pattern_tag_ids(row["id"])
            patterns.append(p)
        return patterns

    def update_pattern(self, pattern: Pattern) -> None:
        """Update an existing pattern's data."""
        pattern.updated_at = datetime.now(timezone.utc)
        mapping_tags_json = json.dumps(pattern.mapping_tags) if pattern.mapping_tags else ""
        self.conn.execute(
            "UPDATE pattern SET updated_at = ?, raw_code = ?, objects_only = ?, "
            "object_count = ?, circle_count = ?, slider_count = ?, "
            "timing_bpm = ?, timing_bpm_min = ?, timing_bpm_max = ?, "
            "artist = ?, title = ?, mapper = ?, mapping_tags = ?, "
            "user_image = ?, user_image_preview = ?, user_image_filename = ? WHERE id = ?",
            (
                pattern.updated_at.isoformat(),
                pattern.raw_code,
                pattern.objects_only,
                pattern.object_count,
                pattern.circle_count,
                pattern.slider_count,
                pattern.timing_bpm,
                pattern.timing_bpm_min,
                pattern.timing_bpm_max,
                pattern.artist,
                pattern.title,
                pattern.mapper,
                mapping_tags_json,
                pattern.user_image,
                pattern.user_image_preview,
                pattern.user_image_filename,
                pattern.id,
            ),
        )
        self.conn.commit()
        self._notify_search_sync(pattern_id=pattern.id)

    def delete_pattern(self, pattern_id: int) -> None:
        """Delete a pattern by id. Related pattern_tag entries are removed via CASCADE."""
        self.conn.execute("DELETE FROM pattern WHERE id = ?", (pattern_id,))
        self.conn.commit()
        self._notify_search_sync_remove(pattern_id)

    # -- Tag-Pattern relationships --

    def add_tag_to_pattern(self, pattern_id: int, tag_id: int) -> None:
        """Link a tag to a pattern. Silently skips if already linked."""
        self.conn.execute(
            "INSERT OR IGNORE INTO pattern_tag (pattern_id, tag_id) VALUES (?, ?)",
            (pattern_id, tag_id),
        )
        self.conn.commit()
        self._notify_search_sync(pattern_id=pattern_id)

    def remove_tag_from_pattern(self, pattern_id: int, tag_id: int) -> None:
        """Unlink a tag from a pattern."""
        self.conn.execute(
            "DELETE FROM pattern_tag WHERE pattern_id = ? AND tag_id = ?",
            (pattern_id, tag_id),
        )
        self.conn.commit()
        self._notify_search_sync(pattern_id=pattern_id)

    def get_pattern_tags(self, pattern_id: int) -> list[Tag]:
        """Return all tags linked to a given pattern."""
        rows = self.conn.execute(
            "SELECT t.id, t.name, t.category "
            "FROM tag t "
            "JOIN pattern_tag pt ON pt.tag_id = t.id "
            "WHERE pt.pattern_id = ? "
            "ORDER BY t.name",
            (pattern_id,),
        ).fetchall()
        return [Tag(id=r["id"], name=r["name"], category=r["category"]) for r in rows]

    def get_tags_with_pattern_count(self) -> list[dict[str, Any]]:
        """Return all tags with the number of patterns they are linked to."""
        rows = self.conn.execute(
            "SELECT t.id, t.name, t.category, COUNT(pt.pattern_id) AS pattern_count "
            "FROM tag t "
            "LEFT JOIN pattern_tag pt ON pt.tag_id = t.id "
            "GROUP BY t.id "
            "ORDER BY pattern_count DESC, t.name"
        ).fetchall()
        return [
            {
                "id": r["id"],
                "name": r["name"],
                "category": r["category"],
                "pattern_count": r["pattern_count"],
            }
            for r in rows
        ]

    def get_patterns_by_tag(self, tag_id: int) -> list[Pattern]:
        """Return all patterns linked to a given tag."""
        rows = self.conn.execute(
            "SELECT p.id, p.created_at, p.updated_at, p.raw_code, p.objects_only, "
            "p.object_count, p.circle_count, p.slider_count, p.timing_bpm, "
            "p.timing_bpm_min, p.timing_bpm_max, "
            "p.artist, p.title, p.mapper, p.mapping_tags, "
            "p.user_image, p.user_image_preview, p.user_image_filename "
            "FROM pattern p "
            "JOIN pattern_tag pt ON pt.pattern_id = p.id "
            "WHERE pt.tag_id = ? "
            "ORDER BY p.created_at DESC",
            (tag_id,),
        ).fetchall()
        patterns: list[Pattern] = []
        for row in rows:
            p = Pattern(
                id=row["id"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
                raw_code=row["raw_code"],
                objects_only=row["objects_only"],
                object_count=row["object_count"],
                circle_count=row["circle_count"],
                slider_count=row["slider_count"],
                timing_bpm=row["timing_bpm"],
                timing_bpm_min=row["timing_bpm_min"],
                timing_bpm_max=row["timing_bpm_max"],
                artist=row["artist"],
                title=row["title"],
                mapper=row["mapper"],
                mapping_tags=json.loads(row["mapping_tags"]) if row["mapping_tags"] else [],
                user_image=row["user_image"] if row["user_image"] is not None else b"",
                user_image_preview=(
                    row["user_image_preview"] if row["user_image_preview"] is not None else b""
                ),
                user_image_filename=row["user_image_filename"] or "",
            )
            p.tag_ids = self._get_pattern_tag_ids(row["id"])
            patterns.append(p)
        return patterns

    def set_pattern_tags(self, pattern_id: int, tag_ids: list[int]) -> None:
        """Replace all tag links for a pattern with the given tag_id list."""
        self.conn.execute(
            "DELETE FROM pattern_tag WHERE pattern_id = ?", (pattern_id,)
        )
        for tag_id in tag_ids:
            self.conn.execute(
                "INSERT INTO pattern_tag (pattern_id, tag_id) VALUES (?, ?)",
                (pattern_id, tag_id),
            )
        self.conn.commit()
        self._notify_search_sync(pattern_id=pattern_id)

    # -- Helpers --

    def _get_pattern_tag_ids(self, pattern_id: int) -> list[int]:
        """Return the tag_ids linked to a pattern."""
        rows = self.conn.execute(
            "SELECT tag_id FROM pattern_tag WHERE pattern_id = ?", (pattern_id,)
        ).fetchall()
        return [r["tag_id"] for r in rows]

    def _notify_search_sync(self, pattern_id: int | None = None) -> None:
        """Notify the search engine to sync the FTS5 index.

        Called after any pattern or tag modification to keep the FTS5
        index in sync. Uses a module-level reference to avoid circular imports.

        If pattern_id is provided, only that pattern is re-synced via
        sync_fts(pattern_id). If None, the full table is rebuilt via
        sync_fts_all() (used for tag-level changes that affect many patterns).
        """
        if _search_engine is not None:
            try:
                if pattern_id is not None:
                    _search_engine.sync_fts(pattern_id)  # type: ignore[attr-defined]
                else:
                    _search_engine.sync_fts_all()  # type: ignore[attr-defined]
            except Exception:
                logger.warning("FTS5 sync failed", exc_info=True)

    def update_pattern_user_image(
        self,
        pattern_id: int,
        user_image: bytes,
        filename: str,
        user_image_preview: bytes = b"",
    ) -> None:
        """Update a pattern's user image and preview data.

        Args:
            pattern_id: The id of the pattern to update.
            user_image: Resized thumbnail image bytes (PNG format).
            filename: Original filename for reference.
            user_image_preview: Resized preview image bytes (PNG format).
        """
        self.conn.execute(
            "UPDATE pattern SET user_image = ?, user_image_preview = ?, "
            "user_image_filename = ? WHERE id = ?",
            (user_image, user_image_preview, filename, pattern_id),
        )
        self.conn.commit()

    def _notify_search_sync_remove(self, pattern_id: int) -> None:
        """Notify the search engine to remove a pattern from FTS5 index."""
        if _search_engine is not None:
            try:
                _search_engine.remove_from_fts(pattern_id)  # type: ignore[attr-defined]
            except Exception:
                logger.warning("FTS5 sync failed", exc_info=True)

    # -- Custom mapping tags --

    def get_all_custom_tags(self) -> list[dict]:
        """Return all custom mapping tags."""
        rows = self.conn.execute(
            "SELECT id, tag_name, enabled, created_at "
            "FROM custom_mapping_tags ORDER BY tag_name"
        ).fetchall()
        return [
            {"id": r["id"], "name": r["tag_name"], "enabled": bool(r["enabled"]),
             "created_at": r["created_at"]}
            for r in rows
        ]

    def add_custom_tag(self, name: str) -> bool:
        """Add a custom mapping tag. Returns True on success, False on duplicate."""
        try:
            self.conn.execute(
                "INSERT INTO custom_mapping_tags (tag_name) VALUES (?)", (name,)
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def update_custom_tag_enabled(self, tag_id: int, enabled: bool) -> None:
        """Update whether a custom tag is enabled."""
        self.conn.execute(
            "UPDATE custom_mapping_tags SET enabled = ? WHERE id = ?",
            (1 if enabled else 0, tag_id)
        )
        self.conn.commit()
