#!/usr/bin/env python3
from typing_extensions import TypedDict, Annotated, Literal
import operator

class PatientState(TypedDict, total=False):
    mode: Literal["initialize", "reply", "evaluate", 'question', 'test', 'unrelated']
    profile: str
    messages: Annotated[list[dict[str, str]], operator.add] 
    query: str
    response: str
    introduction: str
    emotion: str
    facts: list[str]
    chunk_ids: list[int]
    options: dict
    n_rag_facts: int
    use_hyde: bool
    llm_loops: int
