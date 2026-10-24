#!/usr/bin/env python3
from pathlib import Path
import sqlite3

class HistoryDB:
    def __init__(self):
        history_file = Path('data/chat.db')
        schema_file = Path('data/schema.history.sql')

        history_file.touch()
        self.con = sqlite3.connect(history_file)
        self.con.row_factory = sqlite3.Row

        # Setup database if empty
        with self.con as db:
            result = db.execute('SELECT name from sqlite_master;')
            tables = [row['name'] for row in result.fetchall()]
        # Db is empty, so initialize
        if not tables:
            with open(schema_file) as f, self.con as db:
                db.executescript(f.read())

    # Adds the patient casefile and returns the patient id
    def add_patient(self, profile: str) -> int:
        with self.con as db:
            result = db.execute('''
                INSERT INTO chats (patient_profile)
                VALUES (?);
            ''', [profile]
            )
            return result.lastrowid

    def add_chat(self, chat_id: int, query: str, response: str, chunk_ids: list[int]) -> None:
        with self.con as db:
            result = db.execute('''
                INSERT INTO histories (chat_id, query, response)
                VALUES (?, ?, ?);
            ''', [chat_id, query, response]
            )
            query_id = result.lastrowid
            for chunk in chunk_ids:
                result = db.execute('''
                    INSERT INTO facts (history_id, chunk_id)
                    VALUES (?, ?);
                ''', [query_id, chunk]
                )
        
    # Remove messages about a patient
    def delete_patient(self, chat_id: int) -> None:
        with self.con as db:
            result = db.execute('''
                DELETE FROM chats
                WHERE id = ?;
            ''', [chat_id]
            )
