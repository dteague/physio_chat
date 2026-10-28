#!/usr/bin/env python3
import ollama 
import random
from pathlib import Path

from .state import PatientState
from .embedding import EmbeddingDB

###############################
####       CONSTANTS       ####
###############################

MODEL = 'llama3.2'
CATEGORY_MODEL = 'tev1:0.8b'
  
EMOTIONS = [
    "angry", "disgusted", "interested", "joyful", "trusting", "fearful",
    "distracted", "sad", "bored", "annoyed", "neutral",
]

PATIENT_PROMPT = """You are a patient with endometriosis who is visiting a physical therapy clinic for one or more musculoskeletal disorders.
Your chats are being used for a role play with physical therapy students to help them learn how to diagnose your problem
and create a treatment plan. Respond as if you were a real patient.
Keep the replies quite short and in a casual style. Do not use technical terms and ask questions about technical terms if the user uses one with you.
"""

embedding = EmbeddingDB(Path("data/embeddings.db"), embedding_tbl='vectors', use_ann=True)

###############################
####   HELPER FUNCTIONS    ####
###############################

def _chat(messages: list[dict[str, str]], state: PatientState) -> str:
    reply = ollama.chat(
        model=MODEL,
        messages=messages,
        options=state.get("options") or {},
    )
    return reply["message"]["content"]

@staticmethod
def _route(state: PatientState) -> str:
    mode = state["mode"]
    if mode not in ("initialize", "reply", "evaluate"):
        raise ValueError(f"Unsupported mode: {mode}")
    return mode


def _neighbors(query: str, state: PatientState):
    if state.get("use_hyde", False):
        query = _chat([
            {"role": "system", "content": "You are creating an answer to a physical therapy question to improve retrieval of relevant documents. Answer the question."},
            {"role": "user", "content": query},
        ], state)
    return embedding.get_neighbors(query, state.get("n_rag_facts", 2))


###############################
####        NODE           ####
###############################

def select_message_type(state: PatientState):
    # Need to initialize state
    if 'profile' not in state:
        return {"mode": "initialize"}

    # Find out how to treat query
    choices = ollama.systemone(
        model=CATEGORY_MODEL, state=state['query'],
        questions= {
            'label': {
                'type': 'choice',
                'instructions': "How would this question be classified given the context of a therapist asking it to a patient at a physical therapy clinic",
                'criteria': {
                    'question': "Asking a question related to physical therapy or history of the patient",
                    'test': "Asking patient to perform an exercise or asking the results of a physical manipulation",
                    'evaluation': 'Giving a treatment or plan',
                    'unrelated': 'Question or comment is unrelated to physical therapy'
                }
            }

        }
    )
    print(choices['answers']['label'])
    return {
        "mode": choices['answers']['label']['choice'],
        "llm_loops": 0
    }


def profile_facts(state: PatientState) -> dict:
    query = "What are common symptoms of endometriosis especially needing physical therapy?"
    neighbors = _neighbors(query, state)
    return {
        "facts": [row.text for row in neighbors],
        "chunk_ids": [row.rowid for row in neighbors]
    }

def generate_profile(state: PatientState) -> dict:
    user_message = """Create a patient profile for someone visiting a physical therapist with one or more musculoskeletal disorders.
For this patient profile, include only the following: basic demographic information, medical history, current
symptoms (both related to endometriosis and the musculoskeletal disorder(s)), past medical treatment,
and your goals for the treatment."""
    system_message = PATIENT_PROMPT + "\nUse the following information to help create realistic symptoms:\n" + "\n".join(state["facts"])
    profile = _chat([
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_message},
    ], state)
    return {"profile": profile}


def introduction(state: PatientState) -> dict:
    emotion = random.choice(EMOTIONS)
    system_message = PATIENT_PROMPT + f"\nRespond as if you were feeling {emotion} about the therapist meeting.\nPatient profile:\n" + state["profile"]
    intro = _chat([
        {"role": "system", "content": system_message},
        {"role": "user", "content": "Imagine you have just walked into the office of a physical therapist. Introducing yourgive the reason you have come to your appointment and what you are looking for in the meeting."},
    ], state)
    return {
        "emotion": emotion,
        "introduction": intro,
        "messages": [{"role": "assistant", "content": intro}]
    }


def retrieve_facts(state: PatientState) -> dict:
    query = state.get("query", "")
    neighbors = _neighbors(query, state)
    return {
        "facts": [row.text for row in neighbors],
        "chunk_ids": [row.rowid for row in neighbors]
    }


def generate_response(state: PatientState) -> dict:
    query = state.get("query", "")
    system_prompt = (PATIENT_PROMPT +
        "\nBelow is your patient profile and relevant facts. Answer only from this context; if the answer is absent, say so.\n" +
        state.get("profile", "") + "\n" + "\n".join(state.get("facts", [])))
    response = _chat(
        [{"role": "system", "content": system_prompt}]
        + state.get("messages", [])
        + [{"role": "user", "content": query}], state)
    return {
        "response": response,
        "messages": state.get("messages", []) + [
            {"role": "user", "content": query},
            {"role": "assistant", "content": response},
        ],
    }

def perform_exercise(state: PatientState):
    system_message = '''
    You are helping with a role play of a patient-therapist interaction to help
    physical therapist students learn. You have been give a profile of the patient,
    an exercise or test that the patient would do during the therapy session, and facts
    related to the research surrounding these exercises or tests. Pretend the patient performed said
    test, giving the results of the test base on only the information given wrapped in a italic HTML tag.
    '''
    query = "Give a response as if you performed the following request: " + state.get('query', "")
    response = _chat(
        [{"role": "system", "content": system_message}]
        + state.get("messages", [])
        + [{"role": "user", "content": state['query']}], state)
    return {
        "response": response,
        "messages": state.get("messages", []) + [
            {"role": "user", "content": state['query']},
            {"role": "assistant", "content": response},
        ],
    }

def unrelated_message(state: PatientState):
    response = '''
    Your message had nothing to do with the current conversation.
    Please send a message that pertains to the conversation.
    '''
    return {
       "messages": [
           {"role": "user", 'content': state['query']},
           {"role": "assistant", 'content': response}
       ]
    }

def evaluate_treatment(state: PatientState) -> dict:
    system_message = '''
    You are helping with a role play of a patient-therapist interaction to help
    physical therapist students learn. You have been give a profile of the patient,
    the role play conversation, and  that the patient would do during the therapy session, and facts
    related to the research surrounding these exercises or tests. Pretend the patient performed said
    test, giving the results of the test base on only the information given wrapped in a italic HTML tag.
    '''
    query = "Give an evaluatation of the treatment plan that follows: " + state.get('query', "")
    response = _chat(
        [{"role": "system", "content": system_message}]
        + state.get("messages", [])
        + [{"role": "user", "content": query}], state)
    return {
        "response": response,
        "messages": state.get("messages", []) + [
            {"role": "user", "content": query},
            {"role": "assistant", "content": response},
        ],
    }


    
