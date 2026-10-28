"""Persist chats with your existing HistoryDB API; execute AI via PatientGraph.

Place alongside history.py and model_graph.py. No mutable current chat ID.
"""
from langgraph.graph.state import CompiledStateGraph

from .history import HistoryDB
from .state import PatientState
from ..schema import Status, ChatOptions


class ChatService:
    def __init__(self, graph: CompiledStateGraph, history: HistoryDB | None = None):
        self.graph = graph
        self.state = None
        self.options = {}
        self.status: Status = Status.READY
        self.history = history if history is not None else HistoryDB()

    def set_options(self, options: ChatOptions) -> None:
        self.options = options.model_dump()

    def create_empty_chat(self) -> int:
        return self.history.add_patient("temporary", "Initializing...", "none")

    def initialize_chat(self, chat_id: int) -> dict:
        result = self.graph.invoke({
            "mode": "initialize", "options": self.options, "n_rag_facts": 2,
        })
        self.state = result
        self.history.update_patient(chat_id, result["profile"], result["introduction"], result['emotion'])
        return {"chat_id": chat_id, "profile": result["profile"], "introduction": result["introduction"]}

    def set_chat(self, chat_id: int):
        details = self.history.get_patient_messages(chat_id)
        messages = [{"role": "assistant", "content": details.introduction}]
        for message in details.messages:
            messages.extend([
                {"role": "user", "content": message.query},
                {"role": "assistant", "content": message.response},
            ])

        self.state = PatientState(
            profile = details.profile,
            messages = messages,
            introduction = details.introduction,
            emotion = details.emotion
        )

    def get_messages(self, chat_id: int) -> list[dict[str, str]]:
        details = self.history.get_patient_messages(chat_id)
        messages = [{"role": "assistant", "content": details.introduction}]
        for message in details.messages:
            messages.extend([
                {"role": "user", "content": message.query},
                {"role": "assistant", "content": message.response},
            ])
        return messages

    def get_response(self, chat_id: int, query: str,
                     *, n_rag_facts: int = 2, use_hyde: bool = False) -> str:
        details = self.history.get_patient_messages(chat_id)
        result = self.graph.invoke({
            "mode": "reply", "profile": details.profile,
            "messages": self.get_messages(chat_id), "query": query,
            "options": self.options, "n_rag_facts": n_rag_facts, "use_hyde": use_hyde,
        })
        self.state = result
        self.history.add_chat(chat_id, query, result["response"], result["chunk_ids"])
        return result["response"]

    def evaluate_chat(self, chat_id: int) -> str:
        details = self.history.get_patient_messages(chat_id)
        result = self.graph.invoke({
            "mode": "evaluate", "profile": details.profile,
            "messages": self.get_messages(chat_id), "options": self.options,
            "n_rag_facts": 2,
        })
        self.state = result
        query = "Treatment for musculoskeletal disorders for people with endometriosis"
        self.history.add_chat(chat_id, query, result["response"], result["chunk_ids"])
        return result["response"]

    def list_chats(self) -> list[dict]:
        return [{"id": idx, "title": f"Chat #{idx}"} for idx in self.history.get_patient_list()]

    def delete_chat(self, chat_id: int) -> None:
        self.history.delete_patient(chat_id)
