#!/usr/bin/env python3
from pathlib import Path
from pydantic import BaseModel
import sqlite3

class ChatMessage(BaseModel):
    query: str
    response: str

class ChatHistory(BaseModel):
    chat_id: int
    profile: str
    introduction: str
    emotion: str
    messages: list[ChatMessage]


class HistoryDB:
    def __init__(self, filename='chat_history.db'):
        self.history_file = Path('data')/filename
        schema_file = Path('data/schema.history.sql')

        self.history_file.touch()

        # Setup database if empty
        with self.get_connection() as db:
            result = db.execute('SELECT name from sqlite_master;')
            tables = [row['name'] for row in result.fetchall()]
            # Db is empty, so initialize
            if not tables:
                with open(schema_file, 'r') as f:
                    db.executescript(f.read())

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(
            self.history_file,
            timeout=30
        )
        conn.row_factory = sqlite3.Row
        return conn

    # Adds the patient casefile and returns the patient id
    def add_patient(self, profile: str, introduction: str, emotion: str) -> int:
        with self.get_connection() as db:
            result = db.execute('''
                INSERT INTO chats (patient_profile, introduction, emotion)
                VALUES (?, ?, ?);
            ''', [profile, introduction, emotion]
            )
            return result.lastrowid

    def add_chat(self, chat_id: int, query: str, response: str, chunk_ids: list[int]) -> None:
        with self.get_connection() as db:
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
        with self.get_connection() as db:
            result = db.execute('''
                DELETE FROM chats
                WHERE id = ?;
            ''', [chat_id]
            )

    def get_patient_list(self) -> list[int]:
        with self.get_connection() as db:
            result = db.execute('''
                SELECT id
                FROM chats;
            '''
            )
            return [row['id'] for row in result.fetchall()]

    def get_patient_messages(self, chat_id: int):
        with self.get_connection() as db:
            result = db.execute('''
                SELECT
                    patient_profile,
                    introduction,
                    emotion
                FROM chats
                WHERE
                    id = ?;
            ''', [chat_id]
            )
            chat_summary = result.fetchone()

            result = db.execute('''
                SELECT
                    query,
                    response
                FROM histories
                WHERE
                    chat_id = ?
                ORDER BY id;
            ''', [chat_id]
            )
            messages = [ChatMessage(query=r['query'], response=r['response']) for r in result.fetchall()]
            return ChatHistory(
                chat_id=chat_id,
                profile=chat_summary['patient_profile'],
                introduction=chat_summary['introduction'],
                emotion = chat_summary['emotion'],
                messages = messages
            )

    def update_patient(self, chat_id: int, profile: str, introduction: str, emotion: str):
        with self.get_connection() as db:
            result = db.execute('''
                UPDATE chats
                SET
                    patient_profile = ?,
                    introduction = ?,
                    emotion = ?
                WHERE
                    id = ?;
            ''', [profile, introduction, emotion, chat_id]
            )
        
