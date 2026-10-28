#!/usr/bin/env python3
from langgraph.graph import StateGraph, START, END

from .state import PatientState
from .nodes import profile_facts, generate_profile, introduction, retrieve_facts,\
    generate_response, unrelated_message, perform_exercise, select_message_type,\
    evaluate_treatment

def route_mode(state: PatientState) -> str:
    mode_mapper = {
        "initialize": "profile_facts",
        "question": "retrieve_facts",
        "unrelated": "unrelated_message",
        "test": "perform_exercise",
        "evaluate": "evaluate_treatment"
    }
    mode = state.get("mode", None)
    if mode is None or mode not in mode_mapper:
        raise ValueError(f"Unsupported mode: {mode}")
    return mode_mapper[mode]


builder = StateGraph(PatientState)

# add nodes
builder.add_node("profile_facts", profile_facts)
builder.add_node("generate_profile", generate_profile)
builder.add_node("introduction", introduction)
builder.add_node("retrieve_facts", retrieve_facts)
builder.add_node("generate_response", generate_response)
builder.add_node("unrelated_message", unrelated_message)
builder.add_node("perform_exercise", perform_exercise)
builder.add_node("select_message_type", select_message_type)
builder.add_node("evaluate_treatment", evaluate_treatment)

# Add Edges
builder.add_edge(START, "select_message_type")
builder.add_conditional_edges("select_message_type", route_mode) 

# Initialize
builder.add_edge("profile_facts", "generate_profile")
builder.add_edge("generate_profile", "introduction")
builder.add_edge("introduction", END)

# Ask question
builder.add_edge("retrieve_facts", "generate_response")
builder.add_edge("generate_response", END)

# perform exercise test
builder.add_edge("perform_exercise", END)

# Unrelated
builder.add_edge("unrelated_message", END)

# Evaluate
builder.add_edge("evaluate_treatment", END)


graph = builder.compile()
