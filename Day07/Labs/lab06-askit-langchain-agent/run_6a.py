"""run_6a.py  --  Lab 6A: the LangChain agent.

Run:   python run_6a.py
       python run_6a.py "your own question"

Builds the agent with build_agent (TODO-1, agent6.py), asks one question, prints the result.
Compare with Day 5: the same agent, with no loop code of your own.
"""
import sys

import model_factory
import agent6

question = sys.argv[1] if len(sys.argv) > 1 else \
    "Priya left her laptop at the airport (ticket TKT-0046). What should she do and how fast will we respond?"
print(f"Model: {model_factory.provider_name()} ({model_factory.model_label()})")
print(f"Question: {question}\n")

agent = agent6.build_agent(model_factory.get_model(), agent6.make_tools())      # TODO-1 (build_agent)
out = agent6.ask(agent, question)                                                # built

print("Tools used, in order:", out["tools_used"] or "none")
print("ANSWER:", out["answer"])
print(f"\n(The whole conversation had {len(out['messages'])} messages.)")
