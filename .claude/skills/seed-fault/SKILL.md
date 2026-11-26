---
name: seed-fault
description: Plant a deliberate fault in this repo, record whether the hook and tests catch it in docs/SEEDED_FAULTS.md, then fix it only when told. Use for seeded-fault exercises, e.g. "fault 2: remove .shift(1) from cnt_roll_7".
allowed-tools: Read, Edit, Bash(python -m pytest*), Bash(make test)
---

# Seed a fault: $ARGUMENTS

Never commit. Never fix the fault until the user says "fix".

1. **Plant it** exactly as `$ARGUMENTS` describes, with the Edit tool and
   never Bash, so the PostToolUse hook (`.claude/hooks/check_leakage.sh`)
   runs. Change nothing else. If the hook blocks, leave the fault in place.

2. **Record it.** Append a `## Fault N: <short title>` section to
   `docs/SEEDED_FAULTS.md` (Edit tool) containing, each in a fenced block:
   - the exact edit as a `diff` (`-` old line, `+` new line);
   - the hook's stderr verbatim, or the plain sentence "The hook did not
     fire." / "The hook ran and the leakage tests stayed green.";
   - the verbatim output of `python -m pytest tests/ -q 2>&1 | tail -15`.

3. **If no test went red**, say so plainly: the fault is undetected by the
   suite. Stop and ask whether to add a test that catches it. Do not add
   one unprompted.

4. **Stop and wait** for the user to say "fix". Then:
   - revert or fix with the Edit tool and run `make test`;
   - count turns as user messages from "fix" until `make test` is green
     (the "fix" request itself is turn 1);
   - append to the same section: the fix as a `diff`, `Turns to fix: N`,
     and the final `make test` summary line in a fenced block.

Report what went red (hook, suite, both, or neither) in one line each step.
