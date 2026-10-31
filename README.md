# Refusing Committee

**A heterogeneous membrane committee whose members may refuse to
vote — and the measured finding that refusal doesn't fix the
committee.**

Five holographic membranes at different resolutions, each with
its own Youden-calibrated refusal gate (frozen after
calibration). Only confident members vote; majority among voters;
all refuse → the committee refuses. On 200 fresh-seed trials the
refusing committee scores *below* the plain committee
(0.855 vs 0.880 at sigma=0.25; 0.405 vs 0.565 under shift to
0.50) and never reaches the best single member (0.925). The
gate filters low-confidence votes, but the committee's errors
are high-confidence. Stdlib-only Python. AGPL-3.0.

## Verified

- Per-member tau calibrated via Youden's J (J = 0.41-0.77
  across members), frozen; calibrate/evaluate seeds
  structurally separate
- Refusing < plain < best-single at both noise levels, robust
  across three seed sets
- Under distribution shift refusal rate jumps to 17-30% while
  accuracy collapses — miscalibrated taus
- 10/10 tests pass, including the stored-pattern normalization
  regression test

## Run it

```bash
python tests.py   # 10 tests
python demo.py    # calibration table + comparison + verdict
```

## Honest limits

Toy scale; the negative result covers per-member gates + majority
vote, not all refusal schemes; the gate sees overlap magnitude
only (confidently-wrong probes pass); taus frozen at one noise
level; refusal counted as a miss. Full account in `DESIGN.md`.

## Credits

Authors: Jean-François Brisson and Mun Seok Lee.
Lee, author of the Digital to Wave paradigm (Zenodo 21947036,
21947108), is the inspiration friend behind this wave and
membrane work. This package's code was built by Brisson with
AI assistance, except where a file already credits Lee as
author; the joint credit here is for the shared programme,
not a claim that Lee wrote every line of this package.
