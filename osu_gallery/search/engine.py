"""Search/Filter Engine for querying patterns with full-text search and tag filters.

Provides full-text search over pattern content using SQLite FTS5, combined with
tag-based filtering for multi-criteria queries.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from PySide6.QtCore import QObject

from osu_gallery.db.database import GalleryDatabase
from osu_gallery.db.models import Pattern

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Search result
# ---------------------------------------------------------------------------


@dataclass
class SearchQuery:
    """A search query with optional text and tag filters."""

    text: str = ""
    tag_ids: list[int] = field(default_factory=list)
    exclude_tag_ids: list[int] = field(default_factory=list)
    category: str = ""


@dataclass
class SearchResult:
    """A single search result with relevance score."""

    pattern: Pattern
    rank: int = 0


# ---------------------------------------------------------------------------
# Search engine
# ---------------------------------------------------------------------------


class SearchEngine(QObject):
    """Full-text search engine backed by SQLite FTS5.

    Maintains an FTS5 virtual table indexed by pattern raw_code and associated
    tag names. Supports text queries (matched against raw_code and tags) and
    tag-based filtering.
    """

    def __init__(self, db: GalleryDatabase, parent: QObject | None = None) -> None:
        """Initialize the search engine with a database connection.

        Creates the FTS5 virtual table if it does not already exist.

        Args:
            db: The gallery database to query.
            parent: Optional Qt parent object.
        """
        super().__init__(parent)
        self._db = db
        self._fts_table_name = "pattern_fts"
        self._init_fts()

    def _init_fts(self) -> None:
        """Create the FTS5 virtual table if it doesn't exist."""
        self._db.conn.executescript(
            f"""
            CREATE VIRTUAL TABLE IF NOT EXISTS {self._fts_table_name} USING fts5(
                pattern_id UNINDEXED,
                content
            );
            """
        )

    def sync_fts(self, pattern_id: int) -> None:
        """Insert or update the FTS5 entry for a single pattern.

        Rebuilds the searchable text from the pattern's artist, title,
        mapper, raw_code, and associated tag names.
        """
        pattern = self._db.get_pattern(pattern_id)
        if pattern is None:
            self._remove_from_fts(pattern_id)
            return

        tags = self._db.get_pattern_tags(pattern_id)
        tag_text = " ".join(t.name for t in tags)

        searchable = (
            f"{pattern.artist} {pattern.title} {pattern.mapper} "
            f"{pattern.raw_code} {tag_text}"
        )
        self._upsert_fts(pattern_id, searchable)

    def sync_fts_all(self) -> None:
        """Rebuild the entire FTS5 index from the database.

        Uses incremental upserts instead of dropping and recreating the table.
        """
        patterns = self._db.get_all_patterns()
        for pattern in patterns:
            tags = self._db.get_pattern_tags(pattern.id or 0)
            tag_text = " ".join(t.name for t in tags)
            searchable = (
                f"{pattern.artist} {pattern.title} {pattern.mapper} "
                f"{pattern.raw_code} {tag_text}"
            )
            self._upsert_fts(pattern.id, searchable)

    def _upsert_fts(self, pattern_id: int, content: str) -> None:
        """Insert or update a single row in the FTS5 table."""
        existing = self._db.conn.execute(
            f"SELECT COUNT(*) FROM {self._fts_table_name} WHERE pattern_id = ?",
            (pattern_id,),
        ).fetchone()

        if existing and existing[0] > 0:
            self._db.conn.execute(
                f"DELETE FROM {self._fts_table_name} WHERE pattern_id = ?",
                (pattern_id,),
            )

        self._db.conn.execute(
            f"INSERT INTO {self._fts_table_name} (pattern_id, content) "
            "VALUES (?, ?)",
            (pattern_id, content),
        )
        self._db.conn.commit()

    def _remove_from_fts(self, pattern_id: int) -> None:
        """Remove a pattern from the FTS5 index."""
        self._db.conn.execute(
            f"DELETE FROM {self._fts_table_name} WHERE pattern_id = ?",
            (pattern_id,),
        )
        self._db.conn.commit()

    def remove_from_fts(self, pattern_id: int) -> None:
        """Public wrapper for removing a pattern from the FTS5 index."""
        self._remove_from_fts(pattern_id)

    def search(self, query: SearchQuery) -> list[Pattern]:
        """Execute a search query and return matching patterns.

        Combines FTS5 full-text matching with optional tag-based filtering.
        When text is empty, returns all patterns (optionally filtered by tags).
        When text is provided, uses FTS5 to find matching patterns.

        Args:
            query: The search query with text, include tags, exclude tags,
                and optional category filter.

        Returns:
            A list of matching Pattern objects, ordered by relevance.
        """
        if (
            not query.text
            and not query.tag_ids
            and not query.exclude_tag_ids
            and not query.category
        ):
            return self._db.get_all_patterns()

        # Build the base query
        has_where = False
        sql_parts = [
            f"SELECT pattern_id, rank FROM {self._fts_table_name}"
        ]
        params: list[Any] = []

        # Text search via FTS5
        if query.text.strip():
            # Convert spaces to AND logic for multi-word queries,
            # quoting each term to handle special characters like '/'
            terms = query.text.strip().split()
            quoted = []
            for t in terms:
                escaped = t.replace('"', '""')
                quoted.append(f'"{escaped}"')
            fts_query = " AND ".join(quoted)
            sql_parts.append(f"WHERE {self._fts_table_name} MATCH ?")
            params.append(fts_query)
            has_where = True

        # Tag-based filtering
        if query.tag_ids:
            tag_placeholders = ",".join("?" for _ in query.tag_ids)
            and_prefix = "AND" if has_where else "WHERE"
            sql_parts.append(
                f"{and_prefix} pattern_id IN ("
                f"SELECT pattern_id FROM pattern_tag WHERE tag_id IN ({tag_placeholders}))"
            )
            params.extend(query.tag_ids)
            has_where = True

        if query.exclude_tag_ids:
            exclude_placeholders = ",".join("?" for _ in query.exclude_tag_ids)
            and_prefix = "AND" if has_where else "WHERE"
            sql_parts.append(
                f"{and_prefix} pattern_id NOT IN ("
                f"SELECT pattern_id FROM pattern_tag WHERE tag_id IN ({exclude_placeholders}))"
            )
            params.extend(query.exclude_tag_ids)
            has_where = True

        if query.category:
            and_prefix = "AND" if has_where else "WHERE"
            sql_parts.append(
                f"{and_prefix} pattern_id IN ("
                "SELECT pattern_id FROM pattern_tag "
                "JOIN tag ON tag.id = pattern_tag.tag_id "
                "WHERE tag.category = ?)"
            )
            params.append(query.category)
            has_where = True

        if has_where:
            sql_parts.append("ORDER BY rank")

        sql = " ".join(sql_parts)
        rows = self._db.conn.execute(sql, params).fetchall()

        # Fetch full pattern objects
        patterns: list[Pattern] = []
        for row in rows:
            pattern = self._db.get_pattern(row["pattern_id"])
            if pattern is not None:
                pattern.tag_ids = self._db._get_pattern_tag_ids(row["pattern_id"])
                patterns.append(pattern)

        return patterns

    def search_by_tag(self, tag_id: int) -> list[Pattern]:
        """Return all patterns with a given tag, ordered by recency."""
        return self._db.get_patterns_by_tag(tag_id)

    def get_all_tag_names(self) -> list[str]:
        """Return all unique tag names in the database."""
        tags = self._db.get_all_tags()
        return [t.name for t in tags]

    def suggest_tags(self, partial: str) -> list[str]:
        """Suggest tag names matching a partial string (prefix match).

        Args:
            partial: The partial string to match against.

        Returns:
            A list of tag names that start with the partial string, limited to 10.
        """
        if not partial.strip():
            return []

        rows = self._db.conn.execute(
            "SELECT name FROM tag WHERE name LIKE ? ORDER BY name LIMIT 10",
            (partial + "%",),
        ).fetchall()
        return [r["name"] for r in rows]

    def get_search_suggestions(self, partial: str) -> list[str]:
        """Return all searchable terms matching the partial prefix.

        Combines tag names, artist names, song titles, and mapper names
        from the database. Results are deduplicated and limited to 15.

        Args:
            partial: The partial string typed by the user.

        Returns:
            A sorted, deduplicated list of matching terms, limited to 15.
        """
        if not partial.strip():
            return []

        terms: set[str] = set()

        # Tag names (prefix match via FTS-compatible LIKE)
        for row in self._db.conn.execute(
            "SELECT name FROM tag WHERE name LIKE ? ORDER BY name LIMIT 15",
            (partial + "%",),
        ):
            terms.add(row["name"])

        # Artist names
        for row in self._db.conn.execute(
            "SELECT DISTINCT artist FROM pattern "
            "WHERE artist != '' AND artist LIKE ? "
            "ORDER BY artist",
            (partial + "%",),
        ):
            terms.add(row["artist"])

        # Title names
        for row in self._db.conn.execute(
            "SELECT DISTINCT title FROM pattern WHERE title != '' AND title LIKE ? ORDER BY title",
            (partial + "%",),
        ):
            terms.add(row["title"])

        # Mapper names
        for row in self._db.conn.execute(
            "SELECT DISTINCT mapper FROM pattern "
            "WHERE mapper != '' AND mapper LIKE ? "
            "ORDER BY mapper",
            (partial + "%",),
        ):
            terms.add(row["mapper"])

        return sorted(terms)[:15]
