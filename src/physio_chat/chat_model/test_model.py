#!/usr/bin/env python3
from pathlib import Path
from .embedding import EmbeddingDB
from .history import HistoryDB
from ..schema import Status
import random


class Model:
    LANG_MODEL = 'llama3.2'

    def __init__(self):
        self.historydb = HistoryDB('test_chat.db')
        self.chat_history = []
        self.patient_profile = ""
        self.chat_id = -1
        self.status = Status.READY 

    def create_empty_chat(self) -> int:
        self.chat_id = self.historydb.add_patient("temporary", "Initializing...")
        return self.chat_id
    
    def start_chat_agent(self) -> None:
        self.create_agent()
        first_message = self.start_chat()
        self.chat_history.append({'role': "assistant", 'content': first_message})
        self.historydb.update_patient(self.chat_id, self.patient_profile, first_message)
    
    def set_chat(self, chat_id: int):
        if chat_id not in self.historydb.get_patient_list():
            print('error!')
        chat_details = self.historydb.get_patient_messages(chat_id)
        self.chat_id = chat_id
        self.patient_profile = chat_details.profile
        self.chat_history.clear()
        self.chat_history.append({"role": "assistant", 'content': chat_details.introduction})
        for message in chat_details.messages:
            self.chat_history.append({'role': 'user', 'content': message.query})
            self.chat_history.append({'role': 'assistant', 'content': message.response})

    def get_messages(self) -> list[dict]:
        return self.chat_history

    def create_agent(self) -> None:
        self.patient_profile = "This profile is just for testing"

    def start_chat(self) -> str:
        return "I am starting a chat now!"


    def get_response(self, query: str) -> str:
        response = "Hm, that's an interesting question! For that, here is a random number between 1 and 100: "
        response += f'{random.randint(1, 100)}'
        # Update Chat history
        self.chat_history.append({'role': "user", 'content': query})
        self.chat_history.append({'role': "assistant", 'content': response})
        chunks_used = [1, 2, 3]
        self.historydb.add_chat(self.chat_id, query, response, chunks_used)
        return response

    def delete_chat(self) -> None: 
        self.historydb.delete_patient(self.chat_id)
        self.chat_id = -1
        self.patient_profile = ""
        self.chat_history.clear()

    def list_chats(self) -> list[dict]:
        patient_ids = self.historydb.get_patient_list()
        return [{'id': idx, 'title': f'Chat #{idx}' } for idx in patient_ids]

    

    
