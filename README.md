# demo-repo — policy-gate reference example

A minimal, runnable reference for the pattern underneath my AI operations
systems: a **deterministic policy gate** that decides what an agent is allowed
to do on its own, and a **verification gate** that refuses to mark work "done"
without evidence.

The model proposes; the policy disposes. Nothing here calls an LLM — the point
is that the decision is made by a rules table, not a vibe.

## The two gates

**`policy_gate.decide(action)`** classifies an action into exactly one tier:

| Tier | Meaning |
| --- | --- |
| `automatic` | Run it, log it. |
| `notify_and_proceed` | Run it, tell the human. |
| `approval_required` | Stop and wait for explicit human approval. |
| `forbidden` | Deny outright. |

The tier is looked up from an ordered rules table keyed on the action's kind.
Anything not covered by the table is **not** silently allowed — it fails closed
to `approval_required` unless the action is explicitly marked as a read.

**`policy_gate.verify(claim)`** only returns `verified` when the claim carries
fresh, independent evidence. Claimed-but-unproven work is sent back, by design.

## Run it

```bash
python3 -m unittest -v
```

```python
from policy_gate import Action, verify, Claim

decide(Action("read_pnl", read_only=True))          # automatic
decide(Action("draft_email", outbound=True))        # approval_required
decide(Action("wire_funds", moves_money=True))      # forbidden
```

## License

MIT
