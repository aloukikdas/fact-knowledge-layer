import os
import json
import sqlite3
import hashlib
from typing import List, Dict, Any, Optional
from contextlib import contextmanager
from dotenv import load_dotenv

load_dotenv()

DEFAULT_DB_PATH = os.getenv("DATABASE_PATH", "knowledge_layer.db")

class StorageEngine:
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        self._init_db()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT UNIQUE NOT NULL,
                file_hash TEXT UNIQUE NOT NULL,
                total_pages INTEGER NOT NULL,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS facts (
                id TEXT PRIMARY KEY,
                document_name TEXT NOT NULL,
                page_number INTEGER NOT NULL,
                entity TEXT NOT NULL,
                canonical_metric TEXT NOT NULL,
                raw_metric TEXT NOT NULL,
                value TEXT NOT NULL,
                unit TEXT,
                period TEXT,
                scope TEXT,
                accounting_standard TEXT,
                context_notes TEXT,
                evidence_quote TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (document_name) REFERENCES documents(filename)
            )
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS reconciliations (
                id TEXT PRIMARY KEY,
                fact_a_id TEXT NOT NULL,
                fact_b_id TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                explanation TEXT NOT NULL,
                confidence REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (fact_a_id) REFERENCES facts(id),
                FOREIGN KEY (fact_b_id) REFERENCES facts(id)
            )
            """)
            conn.commit()

    def compute_file_hash(self, file_path: str) -> str:
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()

    def register_document(self, filename: str, file_hash: str, total_pages: int) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM documents WHERE file_hash = ? OR filename = ?", (file_hash, filename))
            row = cursor.fetchone()
            if row:
                cursor.execute(
                    "UPDATE documents SET file_hash = ?, total_pages = ?, processed_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (file_hash, total_pages, row[0])
                )
                conn.commit()
                return False
            cursor.execute(
                "INSERT INTO documents (filename, file_hash, total_pages) VALUES (?, ?, ?)",
                (filename, file_hash, total_pages)
            )
            conn.commit()
            return True

    def insert_facts(self, facts: List[Dict[str, Any]]):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for f in facts:
                cursor.execute("""
                INSERT OR REPLACE INTO facts (
                    id, document_name, page_number, entity, canonical_metric, raw_metric,
                    value, unit, period, scope, accounting_standard, context_notes, evidence_quote
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    f["fact_id"], f["document_name"], f["page_number"], f["entity"],
                    f["canonical_metric"], f["raw_metric"], str(f["value"]), f.get("unit"),
                    f.get("period"), f.get("scope"), f.get("accounting_standard"),
                    f.get("context_notes"), f["evidence_quote"]
                ))
            conn.commit()

    def clear_all(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM reconciliations")
            cursor.execute("DELETE FROM facts")
            cursor.execute("DELETE FROM documents")
            conn.commit()

    def insert_reconciliation(self, rec: Dict[str, Any]):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id FROM reconciliations 
                WHERE (fact_a_id = ? AND fact_b_id = ?) 
                   OR (fact_a_id = ? AND fact_b_id = ?)
            """, (rec["fact_a_id"], rec["fact_b_id"], rec["fact_b_id"], rec["fact_a_id"]))
            existing = cursor.fetchone()

            if existing:
                cursor.execute("""
                    UPDATE reconciliations 
                    SET relation_type = ?, explanation = ?, confidence = ?, created_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (rec["relation_type"], rec["explanation"], rec["confidence"], existing[0]))
            else:
                cursor.execute("""
                    INSERT INTO reconciliations (id, fact_a_id, fact_b_id, relation_type, explanation, confidence)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (rec["id"], rec["fact_a_id"], rec["fact_b_id"], rec["relation_type"], rec["explanation"], rec["confidence"]))
            conn.commit()

    def get_all_facts(self, document_name: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if document_name:
                cursor.execute("SELECT * FROM facts WHERE document_name = ? ORDER BY canonical_metric", (document_name,))
            else:
                cursor.execute("SELECT * FROM facts ORDER BY document_name, page_number")
            return [dict(row) for row in cursor.fetchall()]

    def get_reconciliations(self, relation_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = """
            SELECT 
                r.id, r.relation_type, r.explanation, r.confidence,
                fa.document_name as doc_a, fa.page_number as page_a, fa.value as val_a, fa.unit as unit_a, fa.period as period_a, fa.evidence_quote as quote_a, fa.canonical_metric as metric,
                fb.document_name as doc_b, fb.page_number as page_b, fb.value as val_b, fb.unit as unit_b, fb.period as period_b, fb.evidence_quote as quote_b
            FROM reconciliations r
            JOIN facts fa ON r.fact_a_id = fa.id
            JOIN facts fb ON r.fact_b_id = fb.id
            """
            params = ()
            if relation_filter:
                query += " WHERE r.relation_type = ?"
                params = (relation_filter.upper(),)
            query += " ORDER BY r.confidence DESC"
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_stats(self) -> Dict[str, int]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM documents")
            doc_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM facts")
            fact_count = cursor.fetchone()[0]
            cursor.execute("SELECT relation_type, COUNT(*) FROM reconciliations GROUP BY relation_type")
            rel_counts = {row[0]: row[1] for row in cursor.fetchall()}
            return {
                "total_documents": doc_count,
                "total_facts": fact_count,
                "corroborated": rel_counts.get("CORROBORATED", 0),
                "reconciled": rel_counts.get("RECONCILED", 0),
                "contradiction": rel_counts.get("CONTRADICTION", 0),
                "edge_case": rel_counts.get("EDGE_CASE", 0),
            }