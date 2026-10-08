"""run_5a.py  --  Lab 5A: ONE tool call, done by hand.

Run:   python run_5a.py                        (uses a default ticket question)
       python run_5a.py "your own question"

What happens (read the printed lines as they appear):
   1. we send the question to the model, together with the tool specs
   2. the model does NOT answer; it replies "please run tool X with these inputs"      <- tool request
   3. WE run the tool (your run_tool)                                                  <- the model cannot run code
   4. we send the tool's result back, and the model writes the final answer
Nothing to write for this lab: the 3 functions it uses (get_tool_requests, run_tool, make_tool_result) are already built in agent.py.
Read them first, then run this file and watch them work.
"""
import sys

import provider
from agent import final_text, get_tool_requests, make_tool_result, run_tool, short

question = sys.argv[1] if len(sys.argv) > 1 else "What is the status of ticket TKT-0004?"
print(f"Model: {provider.provider_name()} ({provider.model_id()})")
print(f"\n1) Question: {question}")

messages = [{"role": "user", "content": [{"text": question}]}]       # the conversation so far
response = provider.ask_model(messages)                              # the model thinks...

requests = get_tool_requests(response)                               # job 1: find the tool request
if not requests:
    print("\n2) The model asked for NO tool. Its answer:\n  ", final_text(response))
    sys.exit()

blocks = []
for req in requests:
    print(f"\n2) The model asked for the tool  {req['name']}  with inputs  {short(req['input'])}")
    output = run_tool(req["name"], req["input"])                     # WE run the tool (run_tool, job 2)
    print(f"3) We ran it. The tool returned:  {short(output, 200)}")
    blocks.append(make_tool_result(req["id"], output))               # (make_tool_result, job 3)

messages.append(response["output"]["message"])                       # keep the model's request in the conversation
messages.append({"role": "user", "content": blocks})                # ...and add our tool result
response = provider.ask_model(messages)                              # the model reads the result and answers
print("\n4) Final answer from the model:\n  ", final_text(response))
