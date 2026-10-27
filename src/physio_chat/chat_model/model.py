#!/usr/bin/env python3
from pathlib import Path
import ollama
import random

from .embedding import EmbeddingDB
from .history import HistoryDB
from ..schema import Status, ChatOptions

class Model:
    LANG_MODEL = 'llama3.2'
    emotions = ['angry', 'disgusted', 'interested', 'joyful', 'trusting', 'fearful', 'distracted', 'sad', 'bored', 'annoyed ', 'neutral', ]

    def __init__(self):
        embed_db_file = Path('data/embeddings.db')
        embed_tbl_name = 'vectors'
        self.embedding = EmbeddingDB(embed_db_file, embed_tbl_name, True)
        self.options = {}
        
        self.historydb = HistoryDB()
        self.chat_history = []
        self.patient_profile = ""
        self.chat_id = -1
        self.status = Status.READY
        self.n_rag_facts = 2
        self.use_hyde = False

        self.patient_message_base = '''
        You are a patient with endometriosis who is visiting a physical therapy clinic for one or more musculoskeletal disorders.
        Your chats are being used for a role play with physical therapy students to help them learn how to diagnosis your problem
        and create a treatment plan. Respond as if you were a real patient.
        Keep the replies quite short and in a casual style. Do not use technical terms and ask questions about technical terms if the user
        uses on to you. '''

        self.teacher_message_base = '''
        You are acting as the teacher for the physical therapy student in this role play. You are to take all of the messages the user has
        giving and compare them to the literature to see how well it matches.
        '''


    def create_empty_chat(self) -> int:
        self.chat_id = self.historydb.add_patient("temporary", "Initializing...")
        return self.chat_id

    def set_options(self, options: ChatOptions) -> None:
        self.options = options.model_dump()

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

    def get_embedding_facts(self, query: str, n_facts: int) -> list[str]:
        if self.use_hyde:
            system_message = '''
            You are creating an answer to the question, acting as a physical therapist, to refine the results from
            an embedding table for a RAGs model.
            '''
            response = ollama.chat(
                model = self.LANG_MODEL,
                messages = [
                    {'role': 'system', 'content': system_message},
                    {'role': 'user', 'content': query},
                ],
                options = self.options
            )
            query = response['message']['content']
        info = self.embedding.get_neighbors(query, self.n_rag_facts)
        return [item.text for item in info]
        

    def create_agent(self) -> None:
        user_message = '''
        Create a patient profile for someone visiting a physical therapist with one or more musculoskeletal disorders.
        For this patient profile, include only the following: basic demographic information, medical history, current
        symptoms (both related to endometriosis and the musculoskeletal disorder(s)), past medical treatment,
        and your goals for the treatment.'''

        system_message =  self.patient_message_base +'Using the following information to help create realisitic symptoms:\n'

        embedding_query = 'What are common symptoms of endometriosis especially needing physical therapy?'
        info = self.embedding.get_neighbors(embedding_query, self.n_rag_facts)
        system_message += "\n".join([item.text for item in info])

        response = ollama.chat(
            model = self.LANG_MODEL,
            messages = [
                {'role': 'system', 'content': system_message},
                {'role': 'user', 'content': user_message},
            ],
            options = self.options
        )
        self.patient_profile = response['message']['content']

    def start_chat(self) -> str:
        emotion = random.choice(self.emotions)
        system_message = self.patient_message_base + f'''
        You also should response with messages as if you were feeling {emotion} about the therapist meeting.
        Below is your patient profile and list of any facts to use to help answer the questions.\n'''
        system_message += self.patient_profile

        user_message = '''Imagine you have just walked into the office of a physical therapist. Introducing yourself,
        give the reason you have come to your appointment and what you are looking for in the meeting'''

        response = ollama.chat(
            model = self.LANG_MODEL,
            messages = [
                {'role': 'system', 'content': system_message},
                {'role': 'user', 'content': user_message},
            ],
            options = self.options
        )
        return response['message']['content']


    def get_response(self, query: str) -> str:
        system_message =  self.patient_message_base + 'Below is your patient profile and list of facts to use to help answer the questions. Answer only from the context below, and if it is\'t there, say so.\n'
        system_message += self.patient_profile + '\n'

        info = self.embedding.get_neighbors(query, self.n_rag_facts)
        system_message += "\n".join([item.text for item in info])

        messages = [{'role': 'system', 'content': system_message}] \
            + self.chat_history \
            + [{'role': 'user', 'content': query}]
        result = ollama.chat(
            model = self.LANG_MODEL,
            messages = messages,
            options = self.options
        )
        response = result['message']['content']
        # Update Chat history
        self.chat_history.append({'role': "user", 'content': query})
        self.chat_history.append({'role': "assistant", 'content': response})
        chunks_used = [row.rowid for row in info]
        self.historydb.add_chat(self.chat_id, query, response, chunks_used)

        return response

    def evaluate_chat(self) -> str:
        system_message =  self.patient_message_base + 'Below is your patient profile and list of facts to use to help answer the questions. Answer only from the context below, and if it is\'t there, say so.\n'
        system_message += self.patient_profile + '\n'

        query = "Treatment for musculoskeletal disorders for people with endometriosis"
        info = self.embedding.get_neighbors(query, self.n_rag_facts)
        system_message += "\n".join([item.text for item in info])
    
        messages = [{'role': 'system', 'content': system_message}] \
            + self.chat_history \
            + [{'role': 'user', 'content': query}]
        result = ollama.chat(
            model = self.LANG_MODEL,
            messages = messages,
            options = self.options
        )
        response = result['message']['content']
        # Update Chat history
        self.chat_history.append({'role': "user", 'content': query})
        self.chat_history.append({'role': "assistant", 'content': response})
        chunks_used = [row.rowid for row in info]
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

if __name__ == '__main__':
    model = Model()
    model.create_agent()
    model.start_chat()
    

    
