"""run_6c.py  --  Lab 6C: streaming.

Run:   python run_6c.py                 shows each STEP as it happens (your describe_step + stream_answer)
       python run_6c.py --tokens        streams the answer WORD BY WORD (stretch: your stream_tokens)
       python run_6c.py "your question"
It prints how long it took until the first thing appeared.
"""
import sys
import time

import model_factory
import agent6

args = [a for a in sys.argv[1:] if not a.startswith("--")]
question = args[0] if args else "Priya left her laptop at the airport (ticket TKT-0046). What should she do?"
print(f"Model: {model_factory.provider_name()} ({model_factory.model_label()})")
print(f"Question: {question}\n")

agent = agent6.build_agent(model_factory.get_model(), agent6.make_tools(), agent6.GUARDS)
start = time.time()
if "--tokens" in sys.argv:
    pieces = agent6.stream_tokens(agent, question)             # STRETCH-C (optional)
    print(f"\n{len(pieces)} pieces streamed.")
else:
    lines = agent6.stream_answer(agent, question)              # built (TODO-3 is inside describe_step)
    print(f"\n{len(lines)} lines streamed.")
print(f"Total time: {time.time() - start:.1f} s")
