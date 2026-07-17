"""SQLite database layer for osu gallery.

Provides CRUD operations for patterns and tags, with many-to-many
relationship management via the PatternTag junction table.
"""

from __future__ import annotations

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
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
            self._init_schema()
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def _init_schema(self) -> None:
        """Create tables if they don't exist."""
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
                object_count INTEGER NOT NULL DEFAULT 0,
                timing_bpm REAL NOT NULL DEFAULT 0.0
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
            """
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
        object_count: int = 0,
        timing_bpm: float = 0.0,
    ) -> Pattern:
        """Insert a new pattern and return it with its assigned id."""
        now = datetime.now(timezone.utc).isoformat()
        cursor = self.conn.execute(
            "INSERT INTO pattern (created_at, updated_at, raw_code, object_count, timing_bpm) "
            "VALUES (?, ?, ?, ?, ?)",
            (now, now, raw_code, object_count, timing_bpm),
        )
        self.conn.commit()
        self._notify_search_sync()
        return Pattern(
            id=cursor.lastrowid,
            created_at=datetime.fromisoformat(now),
            updated_at=datetime.fromisoformat(now),
            raw_code=raw_code,
            object_count=object_count,
            timing_bpm=timing_bpm,
        )

    def get_pattern(self, pattern_id: int) -> Pattern | None:
        """Return a pattern by id, or None if not found."""
        row = self.conn.execute(
            "SELECT id, created_at, updated_at, raw_code, object_count, timing_bpm "
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
            object_count=row["object_count"],
            timing_bpm=row["timing_bpm"],
            tag_ids=self._get_pattern_tag_ids(row["id"]),
        )

    def get_all_patterns(self) -> list[Pattern]:
        """Return all patterns ordered by created_at descending."""
        rows = self.conn.execute(
            "SELECT id, created_at, updated_at, raw_code, object_count, timing_bpm "
            "FROM pattern ORDER BY created_at DESC"
        ).fetchall()
        patterns: list[Pattern] = []
        for row in rows:
            p = Pattern(
                id=row["id"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
                raw_code=row["raw_code"],
                object_count=row["object_count"],
                timing_bpm=row["timing_bpm"],
            )
            p.tag_ids = self._get_pattern_tag_ids(row["id"])
            patterns.append(p)
        return patterns

    def update_pattern(self, pattern: Pattern) -> None:
        """Update an existing pattern's data."""
        pattern.updated_at = datetime.now(timezone.utc)
        self.conn.execute(
            "UPDATE pattern SET updated_at = ?, raw_code = ?, object_count = ?, timing_bpm = ? "
            "WHERE id = ?",
            (
                pattern.updated_at.isoformat(),
                pattern.raw_code,
                pattern.object_count,
                pattern.timing_bpm,
                pattern.id,
            ),
        )
        self.conn.commit()
        self._notify_search_sync()

    def delete_pattern(self, pattern_id: int) -> None:
        """Delete a pattern by id. Related pattern_tag entries are removed via CASCADE."""
        self.conn.execute("DELETE FROM pattern WHERE id = ?", (pattern_id,))
        self.conn.commit()
        self._notify_search_sync_remove(pattern_id)

    # -- Tag-Pattern relationships --

    def add_tag_to_pattern(self, pattern_id: int, tag_id: int) -> None:
        """Link a tag to a pattern. Raises DatabaseError if the relationship already exists."""
        try:
            self.conn.execute(
                "INSERT INTO pattern_tag (pattern_id, tag_id) VALUES (?, ?)",
                (pattern_id, tag_id),
            )
            self.conn.commit()
            self._notify_search_sync()
        except sqlite3.IntegrityError as err:
            raise DatabaseError(
                f"Tag {tag_id} already linked to pattern {pattern_id}"
            ) from err

    def remove_tag_from_pattern(self, pattern_id: int, tag_id: int) -> None:
        """Unlink a tag from a pattern."""
        self.conn.execute(
            "DELETE FROM pattern_tag WHERE pattern_id = ? AND tag_id = ?",
            (pattern_id, tag_id),
        )
        self.conn.commit()
        self._notify_search_sync()

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
            "SELECT p.id, p.created_at, p.updated_at, p.raw_code, p.object_count, p.timing_bpm "
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
                object_count=row["object_count"],
                timing_bpm=row["timing_bpm"],
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
        self._notify_search_sync()

    # -- Helpers --

    def _get_pattern_tag_ids(self, pattern_id: int) -> list[int]:
        """Return the tag_ids linked to a pattern."""
        rows = self.conn.execute(
            "SELECT tag_id FROM pattern_tag WHERE pattern_id = ?", (pattern_id,)
        ).fetchall()
        return [r["tag_id"] for r in rows]

    def _notify_search_sync(self) -> None:
        """Notify the search engine to sync the FTS5 index.

        Called after any pattern or tag modification to keep the FTS5
        index in sync. Uses a module-level reference to avoid circular imports.
        """
        if _search_engine is not None:
            try:
                _search_engine.sync_fts_all()
            except Exception:
                logger.debug("FTS5 sync failed", exc_info=True)

    def _notify_search_sync_remove(self, pattern_id: int) -> None:
        """Notify the search engine to remove a pattern from FTS5 index."""
        if _search_engine is not None:
            try:
                _search_engine.remove_from_fts(pattern_id)  # type: ignore[attr-defined]
            except Exception:
                logger.debug("FTS5 sync failed", exc_info=True)
