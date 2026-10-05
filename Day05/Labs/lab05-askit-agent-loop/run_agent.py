"""run_agent.py  --  Lab 5B and 5C: run the whole agent loop.

Run:   python run_agent.py "Priya left her laptop at the airport (ticket TKT-0046). What should she do and how fast will we respond?"
       python run_agent.py "Reset the password for EMP-1021"            (a write tool: Lab 5C asks you to approve)
       python run_agent.py --raw "What is the status of ticket TKT-0004?"   (also prints the raw conversation)

It prints every step as it happens, then the answer, the number of steps, the tokens and the estimated cost.
"""
import json
import sys

import provider
from agent import run_agent

args = [a for a in sys.argv[1:] if a != "--raw"]
question = args[0] if args else "What is the status of ticket TKT-0004?"
print(f"Model: {provider.provider_name()} ({provider.model_id()})")
print(f"Question: {question}\n")

result = run_agent(question)                                  # <- the loop you built in agent.py

print("\n" + "=" * 60)
print("ANSWER:", result["answer"])
print(f"Steps: {result['steps']}   Handoff to human: {result['handoff']}")
cost = provider.cost_usd(provider.model_id(), result["input_tokens"], result["output_tokens"])
print(f"Tokens: {result['input_tokens']} in + {result['output_tokens']} out   Estimated cost: ${cost:.5f}")
if "--raw" in sys.argv:
    print("\nRAW CONVERSATION (what was really sent to the model):")
    print(json.dumps(result["messages"], indent=2, ensure_ascii=False))
