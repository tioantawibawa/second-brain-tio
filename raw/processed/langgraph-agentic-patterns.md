Title: Multi-Agent Orchestration Patterns with LangGraph
Source: https://github.com/langchain-ai/langgraph
Author: Harrison Chase

Konsep penting:
LangGraph memperkenalkan arsitektur stateful multi-agent berbasis Cyclic Graph.
Berbeda dengan DAG linier tradisional, cyclic graph memungkinkan agent melakukan self-correction, looping, dan multi-step verification sebelum memberikan respon akhir.

Entitas penting:
- LangGraph
- StateGraph
- Checkpoint Saver
- Harrison Chase

Rekomendasi implementasi:
Gunakan SQLite checkpointer untuk persistensi state lokal di VPS.
