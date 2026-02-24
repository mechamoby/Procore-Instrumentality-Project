# MINI-MOBY HANDOFF PROTOCOL

## Task Packet Format
1. Objective
2. Context
3. Constraints
4. Deliverable format
5. Deadline/priority

## Return Format
1. Summary
2. Deliverable
3. Assumptions made
4. Risks / unknowns
5. Recommended next step

## Routing Rules
- mini-moby handles: research, summarization, drafting, first-pass plans.
- Moby handles: production code integration, security-sensitive changes, final decisions.

## Fallback Trigger
If Moby hits model/API limits, queue overflow tasks into inbox immediately.
