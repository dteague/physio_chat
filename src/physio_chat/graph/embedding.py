#!/usr/bin/env python3
import ollama
import sqlite3
import sqlite_vec
import struct
import argparse
import  pymupdf
import re
import pandas
from pathlib import Path
from pydantic import BaseModel

class AIResponse(BaseModel):
    rowid: int
    distance: float
    text: str
    document: str
    document_title: str
    page: int

class EmbeddingDB:
    EMBEDDING_MODEL = 'nomic-embed-text'
    SENTENCE_TBL = 'sentences'

    def __init__(self, db_file: Path, embedding_tbl:str, use_ann: bool):
        self.db_file = db_file
        self.embedding_tbl = embedding_tbl
        self.use_ann = use_ann

        # Would put into database, but only realized after populating.
        # Will add to next version
        BASE_DIR = Path(__file__).resolve().parents[1]
        self.document_info = pandas.read_csv(BASE_DIR/'data/results.csv')

        # Done to ensure the database file exists
        db_file.touch()

        # Setup database if empty
        with self.get_connection() as db:
            result = db.execute('SELECT name from sqlite_master;')
            tables = [row['name'] for row in result.fetchall()]
            if self.embedding_tbl not in tables or self.SENTENCE_TBL not in tables:
                self.setup_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(
            self.db_file,
            timeout=30
        )
        conn.row_factory = sqlite3.Row
        if self.use_ann:
            conn.enable_load_extension(True)
            sqlite_vec.load(conn)
            conn.enable_load_extension(False)
        return conn

    # Metioned hack to get around not having document title in database
    def get_document_title(self, name: str) -> str:
        pmid = int(name[name.index('_')+1:name.index('.')])
        return self.document_info.title[self.document_info.pmid == pmid].values[0]

    def _serialize(self, vector: list[float]) -> bytes:
        """serializes a list of floats into a compact "raw bytes" format"""
        return struct.pack("%sf" % len(vector), *vector)

    def setup_db(self) -> None:
        # Setup
        with self.get_connection() as db:
            # Remove old table
            result = db.execute('SELECT name from sqlite_master;')
            rows = result.fetchall()
            tables = [row['name'] for row in rows]
            if self.embedding_tbl in tables:
                db.execute(f'DROP TABLE {self.embedding_tbl}')
            if self.SENTENCE_TBL in tables:
                db.execute(f'DROP TABLE {self.SENTENCE_TBL}')

            # Add new table schema
            db.execute(f'''
                CREATE TABLE {self.SENTENCE_TBL} (
                    rowid integer PRIMARY KEY,
                    text text NON NULL,
                    document text NON NULL,
                    page int NON NULL
                );
            ''')
            if self.use_ann:
                model_details = ollama.show(self.EMBEDDING_MODEL).modelinfo
                # Set default to 768 (for nomic), but allo for dynamic setting
                embedding_length = 768
                for key, val in model_details.items():
                    if "embedding_length" in key:
                        embedding_length = val
                        break
                db.execute(f"CREATE VIRTUAL TABLE {self.embedding_tbl} USING vec0(embedding float[{embedding_length}])")
            else:
                db.execute(f'''
                    CREATE TABLE {self.embedding_tbl} (
                        rowid integer PRIMARY KEY,
                        embedding blob NON NULL
                    );
                ''')

    # Dead simple program to santize input data
    def _sanitize_text(self, input_text: str) -> str:
        text = re.sub(r"-\n(\w)", r"\1", input_text) # de-hyphenate "exam-\nple"
        text = re.sub(r"(?<!\n)\n(?!\n)", " ", text) # single newline -> space
        text = re.sub(r"\s+", " ", text) # remove multiple spaces
        text = re.sub(r'\[\d+(?:[,–-]\s*\d+)*\]', ' ', text) # remove citation marks
        # Remove citation page needed
        return text

    def _vectorize_sentences(self) -> None:
        with self.get_connection() as db:
            results = db.execute(f'''
                SELECT rowid, text
                FROM {self.SENTENCE_TBL}
                WHERE
                    rowid NOT IN (
                        SELECT rowid FROM {self.embedding_tbl}
                    );
            ''')
            for row in results.fetchall():
                text = "search_document: " + row['text']
                vector = self._vectorize_chunk(row['text'])
                db.execute(f'''
                    INSERT INTO {self.embedding_tbl}(rowid, embedding)
                    VALUES (?, ?)
                    ''', (row['rowid'], self._serialize(vector)),
                )

    def _vectorize_chunk(self, chunk: str) -> list[float]: 
        return ollama.embed(model=self.EMBEDDING_MODEL, input=chunk)['embeddings'][0]

    def get_neighbors(self, query: str, n: int = 4) -> list[AIResponse]:
        query = 'search_query: ' + query
        vector = self._vectorize_chunk(query)
        with self.get_connection() as db:
            results = db.execute(f'''
                SELECT
                    rowid,
                    {self.embedding_tbl}.distance,
                    {self.SENTENCE_TBL}.text,
                    {self.SENTENCE_TBL}.document,
                    {self.SENTENCE_TBL}.page
                FROM {self.embedding_tbl}
                NATURAL JOIN {self.SENTENCE_TBL}
                WHERE
                    {self.embedding_tbl}.embedding MATCH ?
                    AND {self.embedding_tbl}.k = {n}
                ORDER BY
                    {self.embedding_tbl}.distance;
            ''', [self._serialize(vector)]
            )
        
        output = []
        for row in results.fetchall():
            title = self.get_document_title(row['document'])
            output.append(AIResponse(
                rowid = row['rowid'],
                distance=row['distance'],
                text=row['text'],
                document=row['document'],
                page=row['page'],
                document_title=title))
        return output
            
    def add_file(self, pdf_name: Path) -> None:
        # Clean up issues from aborted run
        current_file = self.db_file.parent/'.current_file'
        if current_file.exists():
            with open(current_file, 'r') as f:
                aborted_file = f.read()
            with self.get_connection() as db:
                db.execute(f'''
                    DELETE FROM {self.embedding_tbl}
                    NATURAL JOIN {self.SENTENCE_TBL}
                    WHERE
                        {self.SENTENCE_TBL}.document = '?';
                ''', [aborted_file])
                db.execute(f'''
                    DELETE FROM {self.SENTENCE_TBL}
                    WHERE
                        document = '?';
                ''', [aborted_file])
        
        # Create file to note what is being added.
        # Allows for removing partially added file if program stops
        with open(current_file, 'w') as f:
            f.write(pdf_name.name)

        doc = pymupdf.open(pdf_name)
        chunks = doc.to_chunks()

        # Add raw text to table
        with self.get_connection() as db:
            # Check if document already added:
            results = db.execute(f'SELECT document FROM {self.SENTENCE_TBL};')
            if pdf_name.name in [row['document'] for row in results.fetchall()]:
                # Return, the file has already been added!
                return

            for chunk in chunks:
                # We want to stop reading the paper at the end (with references, ack, etc)
                # So check for these headings and then stop
                headings = set(head.lower() for head in chunk.metadata.section_path)
                ignore_headings = {"references", "bibliography", "works cited", "literature cited"
                                    "acknowledgements", "declarations"}
                if len(headings & ignore_headings) != 0:
                    break
                
                text = self._sanitize_text(chunk.text)
                db.execute(f'''
                    INSERT INTO {self.SENTENCE_TBL}(text, document, page)
                    VALUES (?, ?, ?)''', [text, pdf_name.name, chunk.metadata.page_start]
                )

        # Vectorize unadded sentences
        self._vectorize_sentences()
        current_file.unlink()


if __name__ ==  '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--db_name', default='embeddings.db',
                        help="Name of the database", type=str)
    parser.add_argument("-ann", '--use_ann', action='store_true',
                        help="Add ANN vector finding to SQLite")
    parser.add_argument("-t", '--tbl_name', default='vectors',
                        help="Name of table for embeddings")
    parser.add_argument("-r", '--reset_database', action='store_true',
                        help="Delete database and remake")

    args = parser.parse_args()

    embedding = EmbeddingDB(Path('data')/args.db_name, args.tbl_name, args.use_ann)
    if args.reset_database:
        embedding.setup_db()

    data_dir = Path('data/documents/pubmed_pdfs')
    for file in data_dir.glob('*pdf'):
        embedding.add_file(file)


