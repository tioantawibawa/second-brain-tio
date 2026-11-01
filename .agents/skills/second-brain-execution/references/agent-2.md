# Agent 2 — Framework proposal and Codex handoff

Input: the same brief and the completed `01-tasks`. Write only `02-proposal` and `04-execution-prompt`. Keep Agent 1's task IDs stable; explain proposed task changes rather than silently replacing the upstream analysis.

Review the breakdown for missing prerequisites, excessive scope, unverifiable success criteria, and unsupported assumptions. Return proposed task changes to the orchestrator for Agent 1 to reconcile before finalizing; task definitions, dependencies, and scope must agree across both artifacts. Return material blockers instead of fabricating certainty.

Write a concise proposal Tio can decide on:

- Problem, recommendation, intended outcome, scope, and exclusions.
- The framework suited to the actual problem and why it fits. It may be a practical phase structure; do not force a fashionable named framework. Compare alternatives when a meaningful decision exists.
- Phases mapped to task IDs, outputs, prerequisites, acceptance criteria, and rough effort/cost assumptions. Do not invent budgets or validated impact.
- Data, tools, access, risks, validation, and a small set of concrete review decisions. Identify the exact proposed task scope and proposal version for approval/revision/deferral.
- A skill matrix: task or deliverable → available skill and exact name/path → why needed → fallback. Verify skill availability in the current environment. Include the local `second-brain-execution` planning skill; recommend additional skills only if useful.

Write complete copyable prompts in `04-execution-prompt`, replacing any pending scaffold. Include a prompt for the proposed first executable task and a broader approved-phase prompt when useful. Each prompt must contain:

- The actual brief/proposal/task paths and proposal version, task IDs and dependencies, target workspace, required source context, and exact deliverables.
- Relevant skill instructions, acceptance criteria, proportionate checks, expected result reporting, and actual scope constraints.
- A review condition: check explicit human approval for this proposal version/task scope; if absent, present the proposal for review and stop before implementation. Do not embed a sentence pretending Tio has already approved it.

Prompts should be usable as written after approval. If an essential target path or input is genuinely missing, produce a ready-to-copy clarification prompt instead of a fake executable prompt. Explain the blocker in the proposal. Never ship unresolved placeholders disguised as a completed prompt.

Display the recommended prompt and proposal to the user; saving a file alone is insufficient. Do not execute the proposed project in this planning run.
