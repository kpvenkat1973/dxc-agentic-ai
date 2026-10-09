# AskIT Program — Course Map

Each day has its own folder: `DayNN\Content\` holds the session page and `DayNN\Labs\` holds that day's lab code.
New content appears the morning of each session — run `START_DAY.bat` to get it.

| Day | Date | Topic | Session page | Labs | Status |
|---|---|---|---|---|---|
| 1 | Wed 30 Sep | Foundations: landscape, models, LLM mechanics, setup | `Day01\Content` | `Day01\Labs\lab01-hello-llm` | Available |
| 2 | Thu 1 Oct | Not held: content merged into Day 3 | | | Merged |
| — | Fri 2 Oct | No session (holiday) | | | |
| 3 | Mon 5 Oct | Embeddings, chunking and naive RAG (meaning map, cosine vs Euclidean) | `Day03\Content` | `Day03\Labs\lab02-naive-rag`, `lab02-askit-rag-app` | Ready |
| 4 | Tue 6 Oct | Advanced RAG (filter, hybrid, rerank, guard), agentic RAG with critic, evaluation and security | `Day04\Content` | `Day04\Labs\lab03-askit-advanced-rag`, `lab04-askit-agentic-rag` | Ready |
| 5 | Wed 7 Oct | Agents, ReAct, tools and function calling | `Day05\Content` | `Day05\Labs\lab05-askit-agent-loop` | Ready |
| 6 | Thu 8 Oct | LangChain agents, middleware, streaming | `Day06\Content` | `Day06\Labs\lab06-askit-langchain-agent` | Ready |
| 7 | Fri 9 Oct | Context, compaction and memory | `Day07\Content` | `Day07\Labs\lab07-askit-memory-context` | Ready |
| 8 | Mon 12 Oct | Multi-agent and human-in-the-loop | `Day08\Content` | `Day08\Labs\lab09-...` | Coming |
| 9 | Tue 13 Oct | MCP | `Day09\Content` | `Day09\Labs\lab10-...` | Coming |
| 10 | Wed 14 Oct | Observability, cost, evaluation | `Day10\Content` | `Day10\Labs\lab11-...`, `lab13-...` | Coming |
| 11 | Thu 15 Oct | Security, guardrails, red team, UI | `Day11\Content` | `Day11\Labs\lab12-...`, `lab14-...` | Coming |
| 12 | Fri 16 Oct | Production on AWS + capstone | `Day12\Content` | `Day12\Labs\lab15-...`, `lab16-...` | Coming |

Dates and topics may be adjusted as the program progresses.

## Where things live

| Folder | What it is |
|---|---|
| `DayNN\Content\` | The interactive session page for that day |
| `DayNN\Labs\` | That day's lab code, README, tests and your `submission\` evidence |
| `teams\` | Your team's ADRs and review-board files |
| `governance\` | Templates for ADR, review boards and readiness checks |
| `askit_data\`, `askit_core\` | Helpdesk data and shared code used by every lab |
| `progress\` | Written by the portal (live progress) and Day End. Do not edit |
| `solutions\` | Released after each session |
