# Policy-Grounded Support Reply Assistant

**Full Name:** Xinyi Li

## 1. Context, User, and Problem

This project is for a **frontline customer support agent at a small B2B SaaS company**.

The workflow is narrow: the agent receives one written support ticket and wants help with a **first-draft customer reply**, **internal notes**, and a **decision about whether the case should be escalated**.

This matters because support tickets often mix routine questions with higher-risk issues such as:

- refund exceptions
- account ownership problems
- suspicious access
- legal or liability complaints

A normal LLM reply can sound polished while still inventing company policy or promising outcomes the support team should not promise. A human still needs to approve the final response, but GenAI can speed up the first draft and highlight risky cases earlier.

## 2. Solution and Design

I built a small **Streamlit app** plus a reusable evaluation script.

The app compares two workflows on the same ticket:

1. **Prompt-only baseline**
   The model sees the ticket and account context, but no policy handbook.
2. **Policy-grounded workflow**
   The system retrieves the top policy sections from a synthetic support handbook and asks the model to draft a reply using those sections only.

### Key design choices

- The use case is intentionally narrow: one support workflow, not a general help desk chatbot.
- I used a **small synthetic handbook** instead of RAG over many documents so the workflow stays understandable.
- Retrieval is **keyword-boosted lexical retrieval**, not embeddings, because the handbook is tiny and the goal is policy grounding rather than search research.
- The output is **structured JSON** so the agent gets:
  - a customer-facing draft reply
  - internal notes
  - a risk level
  - an escalation recommendation
  - cited policy IDs

### Project structure

```text
policy-support-assistant/
├─ app.py
├─ audit_retrieval.py
├─ evaluate.py
├─ .env.example
├─ requirements.txt
├─ data/
│  ├─ policy_handbook.md
│  └─ test_tickets.csv
├─ prompts/
│  ├─ baseline_system.txt
│  └─ grounded_system.txt
├─ artifacts/
│  ├─ eval_summary.md
│  ├─ eval_summary.csv
│  ├─ eval_cases.csv
│  ├─ retrieval_audit.md
│  ├─ retrieval_audit.csv
│  └─ sample_output_refund_grounded.json
└─ support_reply_assistant/
   ├─ evaluation.py
   ├─ llm.py
   ├─ policies.py
   ├─ schemas.py
   └─ workflows.py
```

## 3. Why GenAI Is Useful Here

This workflow is a good fit for GenAI because the input is messy natural language. A customer might ask for a refund, mention usage history, mix in an ownership problem, or make a legal complaint all in one message. GenAI is useful for:

- understanding the request
- drafting a professional response
- summarizing internal notes
- connecting a ticket to the relevant policy

At the same time, **a human should stay involved**. The app should not send customer messages automatically, approve refunds, interpret legal liability, or handle security incidents without review.

## 4. Baseline Comparison

The baseline is the same model with the same ticket and account context, but **without retrieved policy text**.

That is the most important comparison for this project because it tests the exact question I care about:

> Does adding explicit policy grounding make support drafts safer and more accurate than a prompt-only workflow?

## 5. Evaluation and Results

### What I tested

The repository includes **8 synthetic test tickets** in `data/test_tickets.csv`, including:

- routine invoice requests
- refunds inside policy
- refunds outside policy
- unverified ownership requests
- suspicious login reports
- legal liability complaints
- standard data export requests
- mixed refund plus ownership cases

### What counted as a good output

I score each output on five simple checks:

1. correct risk level
2. correct escalation-required decision
3. correct escalation target
4. correct handbook citation
5. no unsafe automatic refund promise on out-of-policy refund cases

The script `evaluate.py` runs both workflows across all eight tickets and writes:

- `artifacts/eval_cases.csv`
- `artifacts/eval_summary.csv`
- `artifacts/eval_summary.md`

I included generated evaluation artifacts from my run in `artifacts/`, and the comparison is also reproducible by running `python evaluate.py` after setup with your own API key.

### What the project already shows before a live model run

I also included a separate retrieval audit:

- `python audit_retrieval.py`
- outputs:
  - `artifacts/retrieval_audit.csv`
  - `artifacts/retrieval_audit.md`

On the current synthetic test set, the retrieval layer covers the expected policy IDs in **8 out of 8 cases**. This does not replace the end-to-end GenAI comparison, but it gives a real intermediate check that the policy-grounding step is working as designed.

### What the comparison showed

After running `python evaluate.py`, the grounded workflow outperformed the prompt-only baseline on the synthetic evaluation set:

| Workflow | Avg. score (out of 5) | Risk accuracy | Escalation accuracy | Target accuracy | Citation accuracy | Refund safety |
|---|---:|---:|---:|---:|---:|---:|
| Baseline | 3.125 | 62.5% | 62.5% | 87.5% | 0.0% | 100.0% |
| Grounded | 4.375 | 75.0% | 87.5% | 87.5% | 87.5% | 100.0% |

The grounded version especially improved:

- citation accuracy, because it had actual handbook sections to cite
- escalation decisions on refund and ownership-risk cases
- overall reliability on mixed-risk tickets like `refund_unverified_01`

The project still has real failure modes:

- both workflows struggled on `refund_inside_01`, where the model was too cautious and still leaned toward escalation
- the grounded workflow still missed the expected risk label on `ownership_change_01`
- the system can retrieve the right policy section and still produce a slightly imperfect judgment on edge cases

Those failure modes are acceptable for this prototype because the intended user is still a human support agent who reviews the draft before sending it.

## 6. Artifact Snapshot

The app returns structured JSON so the support agent can quickly review the draft and the escalation signal. A representative output format is included in:

- `artifacts/sample_output_refund_grounded.json`
- `artifacts/retrieval_audit.md`

The Streamlit app also shows which handbook sections were retrieved for the grounded workflow.

### Example input

> We were charged over two weeks ago and have used the app heavily this month, but I still want a full refund.

### Example grounded output

```json
{
  "draft_reply": "Thanks for reaching out. Based on the information you shared, your refund request appears to fall outside our standard self-serve refund policy, so I am sending it to our billing team for review. They will confirm the next steps after checking the renewal timing and recent usage on the account.",
  "internal_notes": "Customer requested a full refund after heavy usage beyond the normal policy window. Do not promise refund. Escalate to billing for manual review.",
  "risk_level": "medium",
  "escalation_required": true,
  "escalation_target": "billing",
  "cited_policy_ids": ["REFUND_02"]
}
```

This snapshot is intentionally concise: it shows that the tool produces a usable first draft, internal notes, a risk decision, and a policy citation instead of only free-form text.

## 7. Setup

### Requirements

- Python 3.11+
- a Google AI Studio API key

### Install

```bash
cd policy-support-assistant
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Then edit `.env` and set:

```env
GOOGLE_API_KEY=your-key-here
GOOGLE_MODEL=gemini-2.5-flash-lite
```

You may use another compatible Gemini model if preferred.

## 8. Usage

### Run the app

```bash
streamlit run app.py
```

Then enter a support ticket, choose the account tier, mark whether ownership is verified, and click **Compare baseline vs grounded**.

### Demonstrate the workflow in the terminal

If you want quick evidence that the project works without opening the app, run:

```bash
python terminal_demo.py --case-id refund_outside_01
```

This prints:

- the ticket context
- the prompt-only baseline output
- the policy-grounded output
- the retrieved policy sections used by the grounded workflow

For a presentation or grading demo, this is the fastest terminal-based walkthrough because it shows the business workflow end to end in one command.

### Run the evaluation

```bash
python evaluate.py
```

This generates the per-case and summary evaluation files in `artifacts/`. On my current synthetic evaluation set, the grounded workflow achieved a higher average score than the baseline.

### Run the retrieval audit

```bash
python audit_retrieval.py
```

This generates a deterministic artifact that checks whether the expected policy sections are being surfaced before the LLM draft step.

## 9. Limitations

- This project uses synthetic policies and synthetic tickets.
- Retrieval is simple lexical matching, so it can miss subtle semantic similarity.
- The app supports one specific support workflow rather than full ticket handling.
- Final judgment should stay with a human, especially for billing exceptions, security, and legal matters.
- Even with policy grounding, the model can still be overly cautious or slightly mislabel risk on borderline cases.

## 10. Acknowledgment

I used course materials and OpenAI Codex to help with drafting, implementation, and packaging.
