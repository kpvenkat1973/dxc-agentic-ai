"""run_6b.py  --  Lab 6B: the agent WITH middleware (pii_guard + budget_guard + tool_guard).

Run:   python run_6b.py                  asks a question that contains an email address and a phone number
       python run_6b.py --down           pretends the ticket database is down (to test tool_guard)
       python run_6b.py "your question"
"""
import os
import sys

import model_factory
import agent6

down = "--down" in sys.argv
args = [a for a in sys.argv[1:] if not a.startswith("--")]
if down:
    os.environ["ASKIT_TOOLS_DOWN"] = "1"                  # get_ticket will now raise an error
question = args[0] if args else \
    "Aarav Sharma (aarav.sharma@orbitcorp.example, +91 98765 43210) says ticket TKT-0044 is still open. What is its status?"
print(f"Model: {model_factory.provider_name()} ({model_factory.model_label()})")
print(f"Question as typed: {question}\n")

agent = agent6.build_agent(model_factory.get_model(), agent6.make_tools(), agent6.GUARDS)    # GUARDS = your 3 middleware
out = agent6.ask(agent, question)

print("The question as stored in the conversation:", out["messages"][0].content)
print("Tools used, in order:", out["tools_used"] or "none")
print("ANSWER:", out["answer"])
