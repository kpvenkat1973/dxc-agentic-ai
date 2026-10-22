# ADR-002: How we recommend Orbit Corp runs AskIT

| | |
|---|---|
| **Version** | v1 *(change to v2 in the second file)* |
| **Status** | Proposed |
| **Team** | Team *x* · scribe: *name* |
| **Date** | *today* |

> **What changed and why** *(v2 only; delete this box in v1)*
> *2 lines: what the update was, and which rows you changed.*

---

## 1. Our understanding of the customer *(2 lines, your own words)*
*What do they need, and what are the 2 hardest constraints?*

## 2. Top 3 decision drivers
1.
2.
3.

## 3. Decision table: one row per layer of the stack
Pick a letter from the menu (or write your own mix). In the last column write **why, and what we give up**, in one line.

**Must do (5 rows)**

| Layer | Menu of options (pick one) | Our pick | Why, and what we give up |
|---|---|---|---|
| **Hosting** the agent | **A** AgentCore Runtime · **B** containers on ECS/Fargate · **C** containers on the existing EKS cluster · **D** keep VMs and add a backup | | |
| **Knowledge (RAG)** | **A** managed knowledge base (Bedrock Knowledge Bases) · **B** our own vector store (OpenSearch / pgvector) with our own pipeline · **C** keyword search only · **D** hybrid search + reranker. *Think: freshness, per-document access, cost, who maintains it.* | | |
| **Tools (MCP / Gateway)** | **A** AgentCore Gateway in front of the systems · **B** our own MCP server we run · **C** call the APIs directly inside the agent code. *Think: one place for access and audit vs speed and control.* | | |
| **Guardrails and policy** | **A** instructions in the prompt only · **B** managed content filters (Bedrock Guardrails) · **C** policy at the Gateway (AgentCore Policy) · **D** checks inside each tool · **E** a mix (say which). *Think: which rule must never be broken?* | | |
| **Observability and evaluation** | **A** AgentCore Observability + CloudWatch · **B** a tracing tool (Langfuse / LangSmith) · **C** both · **D** offline evaluation before each release (RAGAS / DeepEval style) · **E** online sampling of live answers. *Think: who debugs at 3 am, and how do we know quality has not dropped?* | | |

**If time allows (3 rows)**

| Layer | Menu of options (pick one) | Our pick | Why, and what we give up |
|---|---|---|---|
| **Model** | **A** one small, cheap model · **B** one large model · **C** small model first, large model for hard questions (routing) · **D** a model hosted only in the EU region | | |
| **Identity** | **A** the agent uses its own account for everything · **B** the agent acts as the logged-in user (company login) · **C** mix: its own account for reads, the user's rights for changes | | |
| **Cost and release** | **A** release directly · **B** versions and a test endpoint, then switch over · **C** also budget alarms and a daily question limit | | |

## 4. Our recommendation to the customer
**We recommend** *(one sentence)* **because** *(top 2 reasons)*.

**Three trade-offs we would say out loud on the call**

| You get | You give up | Because |
|---|---|---|
| | | |
| | | |
| | | |

## 5. Biggest risk and how we reduce it
-

## 6. Go or no-go
**Our answer:** GO / NO-GO / GO WITH CONDITIONS

**Conditions** *(1 to 3, each one checkable)*:
-

**What drives the cost, and one question we would ask the customer about it:**
-
