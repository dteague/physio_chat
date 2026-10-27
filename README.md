# Physio Chat
AI chatbot to simulate a patient visiting a physical therapy clinic. The chatbot will roleplay having some disorder (currently relating to endometriosis), allowing students of physical therapy to ask questions to help diagnosis the problem, offer treatment, and get feedback.

## Features
This project uses multiple techniques to make an accurate chat bot. Currently implemented and showcased are:
- RAG based chatbot using local LLM, served with ollama 
- pyMuPDF for chunking pdf articles pulled from PubMed
- sqlite with a sqlite vector extension for sorting embeddings of articles with ANN retrieval
- HyDE for further improvement of embedded fact retrieval
- Graph framework for the agent decision making using LangGraph
- FastAPI for exposing the model functionality
- Basic web-interface for chats, using sqlite for storing the chat histories

## Getting Started
The project is managed by uv, and the website (currently) is served totally by FastAPI. To install, run

``` sh
uv sync 
```

And to start the chatbot, simply start fastapi in the src directory:

``` sh
cd src/physio_chat
uv run fastapi dev
```

`

