# DESIGN — Deep think: the refusing committee

## The hypothesis

The plain committee's measured failure (membrane-committee v0.1.0):
majority vote underperforms the best single member at every noise
level. A natural fix, fusing the refusing membrane: give each
member its own calibrated refusal gate (tau via Youden's J,
in-library vs OOD, frozen after calibration). Clueless members
stay silent; only confident members vote. Surely silencing the
weak voters fixes the aggregation?

## The finding: no.

200 fresh-seed trials per noise level, each member calibrated on
200 labeled probes at sigma=0.25 (calibration/evaluation seeds
structurally separate):

| sigma | plain committee | refusing (acc) | refusal rate | acc-on-answered | best single |
|-------|-----------------|----------------|--------------|-----------------|-------------|
| 0.25  | 0.880           | 0.855          | 0.015        | 0.868           | 0.925       |
| 0.50  | 0.565           | 0.405          | 0.170        | 0.488           | 0.605       |

sigma=0.50 is distribution shift (calibrated at 0.25, tested
at 0.50). The verdict is robust across three independent
calibration/evaluation seed sets (refusing accuracy 0.795-0.855
vs plain 0.850-0.880 in-distribution; 0.385-0.405 vs 0.550-0.565
under shift).

**Refusal does not fix the committee. It slightly hurts it.**
The mechanism is now clear: the gate sees overlap *magnitude*
only. It filters low-confidence votes, but the committee's
errors are *high-confidence* — members that are wrong with large
overlaps sail through the gate, while the gate also silences
members that would have voted correctly. Removing voters changes
the majority without improving it: accuracy-on-answered (0.868)
is itself below the plain committee (0.880). Under distribution
shift it gets worse: tau calibrated at 0.25 is miscalibrated at
0.50, refusal jumps to 17-30%, and accuracy collapses to 0.405
because the committee refuses probes it could have answered.

## What this falsified

- "Silence the weak voters and the majority gets wiser." Wrong:
  the weak voters were not the problem; confident disagreement
  was.
- "Refusal is a universal robustness upgrade." Wrong here:
  per-member refusal gates compose *against* the majority vote
  under shift. Refusal helps a single membrane facing OOD probes
  (refusing-membrane v0.1.0); it does not transfer to fixing a
  committee's aggregation.

## What it did not falsify

- A *jointly* calibrated committee (taus chosen to optimize the
  committee's vote, not each member's in-vs-OOD separation) might
  work. Untested here, claimed nowhere.
- A smarter aggregator (stacking, learned weights) is still the
  open direction from membrane-committee — this build shows
  refusal is not the shortcut to it.

## Honest limits

- **Toy scale** (3 qubits, 4 patterns, 5 members, fixed voting
  rule). The negative result covers per-member Youden-calibrated
  gates + majority vote, not all refusal schemes.
- **Gate blindness**: the gate sees overlap magnitude only, so
  confidently-wrong probes pass. A gate that could see
  *correctness* would be a different (and much harder) thing.
- **Fixed calibration noise level**: taus frozen at sigma=0.25.
  Adaptive recalibration under shift was not studied.
- **Refusal counted as a miss** in accuracy. In a deployment
  where "I don't know" has real value (defer to a human), the
  trade-off could look different — but on pure accuracy, the
  exchange rate here is bad.
