"""run_7c.py  --  Lab 7C: a note saved in one chat is recalled in a NEW chat.

Run:   python run_7c.py
"""
from langgraph.store.memory import InMemoryStore

import model_factory
import agent7

store = InMemoryStore()                                   # the long-term store (it lives as long as this run)
tools = agent7.make_memory_tools(store, user_id="priya")  # save_note and recall_notes for this user

print(f"Model: {model_factory.provider_name()} ({model_factory.model_label()})\n")

print("--- Chat 1 ---")
agent_1 = agent7.build_agent7(model_factory.get_model(), tools, store=store,
                              system_prompt=agent7.SYSTEM_PROMPT_WITH_MEMORY)
print(agent7.chat(agent_1, "chat-1", ["My laptop is a Dell XPS 13. Please remember that."])[-1])

print("\n--- Chat 2 (a NEW chat, nothing from chat 1 in its memory) ---")
agent_2 = agent7.build_agent7(model_factory.get_model(), tools, store=store,
                              system_prompt=agent7.SYSTEM_PROMPT_WITH_MEMORY)
print(agent7.chat(agent_2, "chat-2", ["Which laptop do I have?"])[-1])

print("\nNotes saved in the store:", agent7.recall(store, "priya") or "none yet (TODO-3 not done)")
