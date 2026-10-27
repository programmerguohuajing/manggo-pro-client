"""
本地数据存储模块：使用 SQLite 保存翻译历史记录与生词本
"""
from core.logging import error as _log_error
import os
import sqlite3
import datetime
from typing import List, Dict, Any, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "history.sqlite3")

class HistoryDB:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_text TEXT NOT NULL,
                    target_text TEXT NOT NULL,
                    source_lang TEXT DEFAULT 'auto',
                    target_lang TEXT DEFAULT 'en',
                    source_type TEXT DEFAULT 'manual', -- 'triple_space', 'selection', 'ocr', 'main_win'
                    is_starred INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
        # 初始化时自动从系统原版 Manggo 导入历史记录
        self.sync_from_original_manggo()

    def sync_from_original_manggo(self) -> int:
        orig_db = os.path.expandvars(r"%APPDATA%\Manggo\Manggo\history\history.sqlite3")
        if not os.path.exists(orig_db):
            return 0
        imported = 0
        try:
            with sqlite3.connect(orig_db) as o_conn, self._get_conn() as my_conn:
                o_cur = o_conn.cursor()
                my_cur = my_conn.cursor()
                o_cur.execute("SELECT type, source_text, result_text, source_language, target_language, created_at FROM history_entries")
                rows = o_cur.fetchall()
                for r in rows:
                    stype, src, tgt, slang, tlang, created_at_ms = r
                    if not src or not tgt:
                        continue
                    clean_src = src.strip()
                    clean_tgt = tgt.strip()
                    my_cur.execute("SELECT id FROM history WHERE source_text = ? AND target_text = ?", (clean_src, clean_tgt))
                    if not my_cur.fetchone():
                        try:
                            dt = datetime.datetime.fromtimestamp(created_at_ms / 1000.0).strftime('%Y-%m-%d %H:%M:%S')
                        except Exception:
                            dt = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        my_cur.execute("""
                            INSERT INTO history (source_text, target_text, source_type, source_lang, target_lang, created_at)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (clean_src, clean_tgt, f"manggo_{stype}", slang or 'auto', tlang or 'auto', dt))
                        imported += 1
                my_conn.commit()
        except Exception as e:
            _log_error("DB", f"Error syncing original manggo history: {e}")
        return imported

    def add_record(self, source_text: str, target_text: str, source_type: str = "manual", source_lang: str = "auto", target_lang: str = "en") -> int:
        src = source_text.strip()
        tgt = target_text.strip()
        if not src or not tgt:
            return -1

        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO history (source_text, target_text, source_type, source_lang, target_lang, created_at)
                VALUES (?, ?, ?, ?, ?, datetime('now', 'localtime'))
            """, (src, tgt, source_type, source_lang, target_lang))
            conn.commit()
            return cursor.lastrowid

    def list_records(self, keyword: str = "", only_starred: bool = False, limit: int = 200) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            query = "SELECT id, source_text, target_text, source_type, is_starred, created_at FROM history WHERE 1=1"
            params = []

            if only_starred:
                query += " AND is_starred = 1"
            if keyword.strip():
                query += " AND (source_text LIKE ? OR target_text LIKE ?)"
                kw = f"%{keyword.strip()}%"
                params.extend([kw, kw])

            query += " ORDER BY id DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            return [
                {
                    "id": r[0],
                    "source_text": r[1],
                    "target_text": r[2],
                    "source_type": r[3],
                    "is_starred": bool(r[4]),
                    "created_at": r[5]
                }
                for r in rows
            ]

    def toggle_star(self, record_id: int) -> bool:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE history SET is_starred = 1 - is_starred WHERE id = ?", (record_id,))
            conn.commit()
            cursor.execute("SELECT is_starred FROM history WHERE id = ?", (record_id,))
            row = cursor.fetchone()
            return bool(row[0]) if row else False

    def delete_record(self, record_id: int):
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM history WHERE id = ?", (record_id,))
            conn.commit()

    def clear_all(self):
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM history WHERE is_starred = 0")
            conn.commit()

db = HistoryDB()
