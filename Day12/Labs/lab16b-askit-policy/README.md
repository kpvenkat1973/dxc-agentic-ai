# Lab 16B: AskIT Policy Lab

**Session 12 · Rules the agent cannot argue with: AgentCore Policy (Cedar)** · about 50 minutes · **no code to write**

| What we do | Why | Outcome | How |
|---|---|---|---|
| Put a **policy engine** in front of your Gateway from yesterday and teach it one rule: **the agent must never reset a VIP's password**. Test it, try to get round it, then fix the weak spot. | A prompt rule is a request the model can ignore. A policy at the Gateway is a lock. Clients ask for this in every security review. | You can write and test a Cedar rule, explain default-deny and "forbid always wins", and show why one lock is not enough. | An app that tests the rules with the real Cedar engine, plus console clicks. |

**Stuck in the console?** Do tabs 2 to 5 with the **Practice gateway**. The lesson is the same.

---

## STEP 0. Open the right folder

**We are doing Lab 16B · AskIT Policy Lab now (`lab16b-askit-policy`).**

1. **VS Code** → **File** → **Open Folder** → paste:

```
C:\AskIT\dxc-agentic-ai\Day12\Labs\lab16b-askit-policy
```

2. **Terminal** → **New Terminal** (the prompt ends with **lab16b-askit-policy**).
3. Start the app:

```
python run.py
```

The browser opens (`http://localhost:8501`). Leave it open.

## The plan (50 minutes)

| Minutes | What |
|---|---|
| 0 to 15 | **Practice** in the app: tabs 1 to 4 with the Practice gateway. |
| 15 to 35 | **Console**: Part A below. Do the same on your real Gateway. |
| 35 to 45 | Back in the app, **My Gateway on AWS**: run tabs 2 to 4 again. |
| 45 to 50 | Tab 5: try to get round the rule. Stretch if you finish. |

## The four rules (in the `policies` folder, and in tabs 3 and 4 of the app)

| Rule | What it says |
|---|---|
| `allow_get_ticket` | permit the tool get_ticket on your Gateway |
| `allow_get_user` | permit the tool get_user on your Gateway |
| `allow_reset_password` | permit the tool reset_password on your Gateway |
| `block_vip_reset_password` | **forbid** reset_password when the id is one of the three VIPs |

The app fills your Gateway ARN into the text. Copy the text from the app (the grey box has a copy button), not from the file.

## PART A. On AWS (console, region N. Virginia us-east-1)

Console names can differ slightly. Follow the idea, not the exact word.

1. Search **Bedrock AgentCore** → left menu **Policy** → **Create policy engine**. Name: `askit-pe-user1xx` (your number). Create. Wait until it is **Active**.
2. Open your **Gateway** (Gateways → `askit-gw-user1xx`). Copy the **Gateway ARN** and paste it in the app, tab 1. Press **Edit**. Under **Policy engine** choose yours, mode **Log only**. Save.
3. In the app (**My Gateway on AWS**) press the button in tab 2. Everything works, because Log only blocks nothing. Now edit the Gateway again: mode **Enforce**. Press the button again. **Everything is denied.** That is default deny.
4. In your policy engine open **Policies** → **Create policy** → write Cedar. Name `allow_get_ticket`, paste the text from tab 3. Repeat for `allow_get_user` and `allow_reset_password`. Wait for **Active**. Tick the three boxes in the app, then run the six requests.
5. Create the fourth policy `block_vip_reset_password` (text from tab 4). Tick the box in the app, predict, run.
6. Tab 5: try to get round your own rule.

## If something goes wrong

| Message | Fix |
|---|---|
| Cannot create the policy engine (access denied) | Tell the trainer: **policy engine access**. Carry on with the Practice gateway. |
| "policy validation" error when you save a rule | Read the message. Usual causes: ARN still has `{{GATEWAY_ARN}}`, a missing `;`, or the action name is not `askit-lambda___reset_password` (three underscores). |
| Everything is denied after you attach the engine | Expected in Enforce mode with no rules. Add the permit rules (step 4). |
| VIP is not blocked | Is the fourth policy **Active**? Is the engine mode **Enforce**? Wait a minute and try again. |
| 403 with no word "policy" | Your AWS user lacks permission on the Gateway. Tell the trainer. |

Your Gateway address and ARN are saved in this folder (`my_gateway.json`). It is never pushed to GitHub. Never put AWS keys in GitHub, wikis or chat.

## Stretch (if you finish early)

- If your Gateway has the knowledge tool `search_kb` (Lab 16A, optional step): ask a knowledge question now. It is **denied**, because no rule permits it. Add the permit rule from `policies\allow_search_kb.cedar`, wait for Active, ask again.
- In the console create a policy **from plain English**: "Never reset the password of the VIP employees EMP-1001, EMP-1012 and EMP-1023". Compare the Cedar it writes with yours. Which is safer? Which would you ship?
- Make `block_vip_reset_password` also catch the small-letter spelling. Then try a space. What does this tell you about lists in rules?

## Clean up

When the session is over, delete your **Gateway** (Targets first, then the Gateway) and your **policy engine** (its policies first, then the engine). The trainer also runs a clean-up.
