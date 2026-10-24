#!/usr/bin/env python3
from pathlib import Path
import ollama
from .embedding import EmbeddingDB
from .history import HistoryDB

class Model:
    LANG_MODEL = 'llama3.2'
    emotions = ['angry', 'disgusted', 'interested', 'joyful', 'trusting', 'fearful', 'distracted', 'sad', 'bored', 'annoyed ', 'neutral', ]

    def __init__(self):
        embed_db_file = Path('data/embeddings.db')
        embed_tbl_name = 'vectors'
        self.embedding = EmbeddingDB(embed_db_file, embed_tbl_name, True)
        
        self.historydb = HistoryDB()
        self.simple_history = []
        self.patient_profile = ""

        self.system_message_base = 'You are a patient with endometriosis who is visiting a physical therapy clinic for one or more musculoskeletal disorders. Your chats are being used for a role play with physical therapy students to help them learn how to diagnosis your problem and create a treatment plan. Respond as if you were a real patient. Keep the replies short and in a casual style, avoiding technical terms. '


    def create_agent(self):
        user_message = "Can you create a patient profile for someone visiting a physical therapist with one or more musculoskeletal disorders? For this patient profile, include only the following: basic demographic information, medical history, current symptoms (both related to endometriosis and the musculoskeletal disorder(s)), past medical treatment, and your goals for the treatment."
        system_message =  self.system_message_base +'Using the following information to help create realisitic symptoms:\n'

        embedding_query = 'What are common symptoms of endometriosis especially needing physical therapy?'
        info = self.embedding.get_neighbors(embedding_query)
        system_message += "\n".join([item.text for item in info])

        response = ollama.chat(
            model = self.LANG_MODEL,
            messages = [
                {'role': 'system', 'content': system_message},
                {'role': 'user', 'content': user_message}
            ],
        )
        self.patient_profile = response['message']['content']

    def start_chat(self):
        system_message = self.system_message_base + f'You also should response with messages as if you were {self.emotions[5]}. Below is your patient profile and list of any facts to use to help answer the questions.\n'
        system_message += self.patient_profile

        user_message = 'Imagine you have just walked into the office of a physical therapist. Introducing yourself, give the reason you have come to your appointment and what you are looking for in the meeting'

        response = ollama.chat(
            model = self.LANG_MODEL,
            messages = [
                {'role': 'system', 'content': system_message},
                {'role': 'user', 'content': user_message},
            ],
            stream = True
        )
        for chunk in response:
            print(chunk['message']['content'], end='', flush=True)


    def get_response(self, query: str):
        system_message =  self.system_message_base + 'Below is your patient profile and list of facts to use to help answer the questions. Answer only from the context below, and if it is\'t there, say so.\n'
        system_message += self.patient_profile + '\n'

        info = self.embedding.get_neighbors(query)
        system_message += "\n".join([item.text for item in info])

        messages = [{'role': 'system', 'content': system_message}] \
            + self.simple_history \
            + [{'role': 'user', 'content': query}]
        response = ollama.chat(
            model = self.LANG_MODEL,
            messages = messages
        )


if __name__ == '__main__':
    model = Model()
    model.create_agent()
    model.start_chat()
    

    
