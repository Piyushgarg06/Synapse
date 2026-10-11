"""SQLite-based persistent index for Synapse."""

from __future__ import annotations

import os
import sqlite3
from typing import Optional

SCHEMA_VERSION = 1

SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL UNIQUE,
    language TEXT NOT NULL,
    has_errors INTEGER NOT NULL DEFAULT 0,
    parse_error INTEGER NOT NULL DEFAULT 0,
    parse_error_message TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS symbols (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    qualified_name TEXT NOT NULL,
    kind TEXT NOT NULL,
    file_id INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    start_byte INTEGER NOT NULL,
    end_byte INTEGER NOT NULL,
    start_line INTEGER NOT NULL,
    start_column INTEGER NOT NULL,
    end_line INTEGER NOT NULL,
    end_column INTEGER NOT NULL,
    ordinal INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS imports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    module_name TEXT NOT NULL,
    imported_names TEXT NOT NULL DEFAULT '',
    alias TEXT,
    is_default INTEGER NOT NULL DEFAULT 0,
    is_namespace INTEGER NOT NULL DEFAULT 0,
    start_line INTEGER,
    end_line INTEGER
);

CREATE TABLE IF NOT EXISTS inheritance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    class_name TEXT NOT NULL,
    base_class_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    caller_qualified_name TEXT NOT NULL,
    callee_name TEXT NOT NULL,
    start_line INTEGER,
    end_line INTEGER
);

CREATE TABLE IF NOT EXISTS references_ (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'syntactic',
    resolved_symbol_id TEXT,
    context_qualified_name TEXT NOT NULL DEFAULT '',
    start_byte INTEGER NOT NULL DEFAULT 0,
    end_byte INTEGER NOT NULL DEFAULT 0,
    start_line INTEGER NOT NULL DEFAULT 0,
    start_column INTEGER NOT NULL DEFAULT 0,
    end_line INTEGER NOT NULL DEFAULT 0,
    end_column INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS edges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    edge_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    file_path TEXT NOT NULL DEFAULT '',
    UNIQUE(edge_type, source_id, target_id)
);

CREATE INDEX IF NOT EXISTS idx_symbols_name ON symbols(name);
CREATE INDEX IF NOT EXISTS idx_symbols_qualified_name ON symbols(qualified_name);
CREATE INDEX IF NOT EXISTS idx_symbols_file_id ON symbols(file_id);
CREATE INDEX IF NOT EXISTS idx_symbols_file_path ON symbols(file_path);
CREATE INDEX IF NOT EXISTS idx_symbols_kind ON symbols(kind);
CREATE INDEX IF NOT EXISTS idx_imports_file_id ON imports(file_id);
CREATE INDEX IF NOT EXISTS idx_calls_file_id ON calls(file_id);
CREATE INDEX IF NOT EXISTS idx_calls_caller ON calls(caller_qualified_name);
CREATE INDEX IF NOT EXISTS idx_calls_callee ON calls(callee_name);
CREATE INDEX IF NOT EXISTS idx_references_file_id ON references_(file_id);
CREATE INDEX IF NOT EXISTS idx_references_name ON references_(name);
CREATE INDEX IF NOT EXISTS idx_references_status ON references_(status);
CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id);
CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id);
CREATE INDEX IF NOT EXISTS idx_edges_type ON edges(edge_type);
CREATE INDEX IF NOT EXISTS idx_files_path ON files(path);
"""


class IndexDB:
    """SQLite-based persistent index."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
    
    def open(self):
        """Open the database connection and ensure schema exists."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._init_schema()
    
    def close(self):
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
    
    def __enter__(self):
        self.open()
        return self
    
    def __exit__(self, *args):
        self.close()
    
    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("Database not open")
        return self._conn
    
    def _init_schema(self):
        """Initialize the database schema."""
        cursor = self.conn.cursor()
        cursor.executescript(SCHEMA_SQL)
        
        # Set schema version if not present
        cursor.execute(
            "INSERT OR IGNORE INTO state (key, value) VALUES ('schema_version', ?)",
            (str(SCHEMA_VERSION),),
        )
        self.conn.commit()
    
    def get_state(self, key: str) -> Optional[str]:
        """Get a state value."""
        row = self.conn.execute(
            "SELECT value FROM state WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else None
    
    def set_state(self, key: str, value: str, *, cursor: Optional[sqlite3.Cursor] = None):
        """Set a state value."""
        c = cursor or self.conn.cursor()
        c.execute(
            "INSERT OR REPLACE INTO state (key, value) VALUES (?, ?)",
            (key, value),
        )
        if cursor is None:
            self.conn.commit()
    
    def get_checkpoint(self) -> Optional[str]:
        """Get the last indexed commit SHA."""
        return self.get_state("checkpoint")
    
    def set_checkpoint(self, sha: str, *, cursor: Optional[sqlite3.Cursor] = None):
        """Set the last indexed commit SHA."""
        self.set_state("checkpoint", sha, cursor=cursor)
    
    def store_file_analysis(self, analysis, *, cursor: Optional[sqlite3.Cursor] = None):
        """Store analysis results for a file.
        
        Replaces any existing data for this file path.
        """
        from synapse.models import FileAnalysis
        c = cursor or self.conn.cursor()
        
        # Delete existing file data (cascades to symbols, imports, etc.)
        c.execute("DELETE FROM files WHERE path = ?", (analysis.file_path,))
        
        # Delete edges originating from this file
        c.execute("DELETE FROM edges WHERE file_path = ?", (analysis.file_path,))
        
        # Insert file record
        c.execute(
            """INSERT INTO files (path, language, has_errors, parse_error, parse_error_message)
               VALUES (?, ?, ?, ?, ?)""",
            (analysis.file_path, analysis.language, 
             int(analysis.has_errors), int(analysis.parse_error),
             analysis.parse_error_message),
        )
        file_id = c.lastrowid
        
        # Insert symbols
        for sym in analysis.symbols:
            c.execute(
                """INSERT OR REPLACE INTO symbols 
                   (id, name, qualified_name, kind, file_id, file_path,
                    start_byte, end_byte, start_line, start_column, end_line, end_column, ordinal)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (sym.symbol_id, sym.name, sym.qualified_name, sym.kind.value,
                 file_id, sym.file_path,
                 sym.location.start_byte, sym.location.end_byte,
                 sym.location.start_line, sym.location.start_column,
                 sym.location.end_line, sym.location.end_column,
                 sym.ordinal),
            )
        
        # Insert imports
        for imp in analysis.imports:
            start_line = imp.location.start_line if imp.location else None
            end_line = imp.location.end_line if imp.location else None
            c.execute(
                """INSERT INTO imports 
                   (file_id, file_path, module_name, imported_names, alias,
                    is_default, is_namespace, start_line, end_line)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (file_id, analysis.file_path, imp.module_name,
                 ",".join(imp.imported_names), imp.alias,
                 int(imp.is_default), int(imp.is_namespace),
                 start_line, end_line),
            )
        
        # Insert inheritance
        for inh in analysis.inheritance:
            c.execute(
                """INSERT INTO inheritance (file_id, file_path, class_name, base_class_name)
                   VALUES (?, ?, ?, ?)""",
                (file_id, analysis.file_path, inh.class_name, inh.base_class_name),
            )
        
        # Insert calls
        for call in analysis.calls:
            start_line = call.location.start_line if call.location else None
            end_line = call.location.end_line if call.location else None
            c.execute(
                """INSERT INTO calls 
                   (file_id, file_path, caller_qualified_name, callee_name,
                    start_line, end_line)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (file_id, analysis.file_path, call.caller_qualified_name,
                 call.callee_name, start_line, end_line),
            )
        
        # Insert references
        for ref in analysis.references:
            c.execute(
                """INSERT INTO references_ 
                   (file_id, file_path, name, status, resolved_symbol_id,
                    context_qualified_name,
                    start_byte, end_byte, start_line, start_column, end_line, end_column)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (file_id, analysis.file_path, ref.name, ref.status.value,
                 ref.resolved_symbol_id, ref.context_qualified_name,
                 ref.location.start_byte, ref.location.end_byte,
                 ref.location.start_line, ref.location.start_column,
                 ref.location.end_line, ref.location.end_column),
            )
        
        if cursor is None:
            self.conn.commit()
    
    def delete_file_data(self, file_path: str, *, cursor: Optional[sqlite3.Cursor] = None):
        """Delete all data associated with a file path."""
        c = cursor or self.conn.cursor()
        c.execute("DELETE FROM files WHERE path = ?", (file_path,))
        c.execute("DELETE FROM edges WHERE file_path = ?", (file_path,))
        # Edges targeting symbols from this file need cleanup
        c.execute(
            """DELETE FROM edges WHERE target_id IN 
               (SELECT id FROM symbols WHERE file_path = ?)""",
            (file_path,),
        )
        if cursor is None:
            self.conn.commit()
    
    def search_symbols(self, query: str, limit: int = 20) -> list[dict]:
        """Search symbols by name.
        
        Ranking: exact match > prefix > substring, then by path and qualified_name.
        """
        rows = self.conn.execute(
            """SELECT id, name, qualified_name, kind, file_path,
                      start_line, end_line
               FROM symbols
               WHERE name LIKE ? OR qualified_name LIKE ?
               ORDER BY 
                   CASE 
                       WHEN name = ? THEN 0
                       WHEN name LIKE ? THEN 1
                       ELSE 2
                   END,
                   file_path,
                   qualified_name
               LIMIT ?""",
            (f"%{query}%", f"%{query}%", query, f"{query}%", limit),
        ).fetchall()
        
        return [dict(row) for row in rows]
    
    def get_file_count(self) -> int:
        """Get the number of indexed files."""
        row = self.conn.execute("SELECT COUNT(*) as cnt FROM files").fetchone()
        return row["cnt"]
    
    def get_symbol_count(self) -> int:
        """Get the number of indexed symbols."""
        row = self.conn.execute("SELECT COUNT(*) as cnt FROM symbols").fetchone()
        return row["cnt"]
    
    def get_edge_count(self) -> int:
        """Get the number of edges."""
        row = self.conn.execute("SELECT COUNT(*) as cnt FROM edges").fetchone()
        return row["cnt"]
    
    def get_error_file_count(self) -> int:
        """Get the number of files with parse errors."""
        row = self.conn.execute(
            "SELECT COUNT(*) as cnt FROM files WHERE parse_error = 1 OR has_errors = 1"
        ).fetchone()
        return row["cnt"]
