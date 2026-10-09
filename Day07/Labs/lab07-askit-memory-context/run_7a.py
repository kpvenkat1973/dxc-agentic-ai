"""run_7a.py  --  Lab 7A: watch the context grow, one bar per model call.

Run:   python run_7a.py
The bar grows every step because the whole chat is sent to the model again each time.
"""
import model_factory
import agent7

QUESTIONS = [
    "Ticket TKT-0004 is mine. What is its status?",
    "How do I reset my VPN password?",
    "And what is the status of TKT-0046?",
    "Which ticket did we talk about first?",
]

print(f"Model: {model_factory.provider_name()} ({model_factory.model_label()})\n")
agent7.reset_log()
agent = agent7.build_agent7(model_factory.get_model(), agent7.make_tools(), [agent7.context_meter])
answers = agent7.chat(agent, "lab7a", QUESTIONS)

print("\nLast answer:", answers[-1])
print(f"Total sent to the model over the chat: {agent7.total_input_tokens():,} tokens")
