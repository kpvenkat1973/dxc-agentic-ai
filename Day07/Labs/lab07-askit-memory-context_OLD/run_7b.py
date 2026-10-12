"""run_7b.py  --  Lab 7B: the same long chat WITHOUT and WITH compaction. Compare the bars and the totals.

Run:   python run_7b.py
Compaction = the agent summarises the old part of the chat once it reaches COMPACT_AT_TOKENS (in agent7.py).
Note: the summary call itself costs a little extra. This run counts only what the agent sends for each answer.
"""
import model_factory
import agent7

LONG_CHAT = [
    "Ticket TKT-0004 is mine. What is its status?",
    "How do I reset my VPN password?",
    "And what is the status of TKT-0046?",
    "Which ticket did we talk about first?",
    "What should I do if the VPN still does not connect after the reset?",
    "Summarise what we have discussed so far in one sentence.",
]


def run(label, use_compaction):
    print(f"\n===== {label} =====")
    model = model_factory.get_model()
    middleware = [agent7.compaction_middleware(model), agent7.context_meter] if use_compaction else [agent7.context_meter]
    agent7.reset_log()
    agent = agent7.build_agent7(model, agent7.make_tools(), middleware)
    answers = agent7.chat(agent, f"lab7b-{use_compaction}", LONG_CHAT)
    print(f"Total sent to the model: {agent7.total_input_tokens():,} tokens")
    print("Last answer:", answers[-1])
    return agent7.total_input_tokens()


print(f"Model: {model_factory.provider_name()} ({model_factory.model_label()})")
without = run("WITHOUT compaction", use_compaction=False)
with_c = run("WITH compaction", use_compaction=True)
print(f"\nSaved by compaction: {without - with_c:,} tokens. (Zero means TODO-2 is not done yet.)")
