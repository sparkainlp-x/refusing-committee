"""Demo: does refusal fix the committee's measured failure?

Pipeline:
  1. Each of 5 members (full, mrg0, mrg1, mrg2, mrg01) calibrates
     its own tau via Youden's J on 200 labeled probes at sigma=0.25
     (in-library noisy probes vs Haar-random OOD), then freezes it.
  2. On FRESH seeds, per sigma in {0.25, 0.50}: refusing-committee
     accuracy, refusal rate, accuracy-on-answered, vs plain
     committee (no refusal) vs best single member.
  sigma=0.50 is distribution shift: calibrated at 0.25, tested
  at 0.50.

Run: python demo.py
"""

import math
import random

from rcommittee import RefusingCommittee, RefusingMember, noisy

S2 = 2 ** -0.5
S3 = 3 ** -0.5
S8 = 1.0 / math.sqrt(8)

PATTERNS = [
    [S2, 0j, 0j, 0j, 0j, 0j, 0j, S2],   # GHZ
    [0j, S3, S3, 0j, S3, 0j, 0j, 0j],   # W
    [1, 0j, 0j, 0j, 0j, 0j, 0j, 0j],    # |000>
    [S8] * 8,                            # |+++>
]

MEMBERS = [
    ("full", set()),
    ("mrg0", {0}),
    ("mrg1", {1}),
    ("mrg2", {2}),
    ("mrg01", {0, 1}),
]

CAL_SEED = 777
EVAL_SEED = 9000
N_TRIALS = 200


def build_committee():
    members = [RefusingMember(name, ms, PATTERNS) for name, ms in MEMBERS]
    reports = [m.calibrate(sigma=0.25, n_in=100, n_ood=100,
                           seed=CAL_SEED + i)
               for i, m in enumerate(members)]
    return RefusingCommittee(members), reports


def evaluate(com, sigma, n=N_TRIALS, seed=EVAL_SEED):
    """Fresh-seed evaluation. Returns dict of metrics."""
    members = com.members
    correct = refused = answered = answered_correct = plain_ok = 0
    single_ok = [0] * len(members)
    for s in range(n):
        rng = random.Random(seed + s)
        label = rng.randrange(len(PATTERNS))
        probe = noisy(PATTERNS[label], sigma, rng)
        status, winner, nv = com.decide(probe)
        if status == "refuse":
            refused += 1
        else:
            answered += 1
            if winner == label:
                correct += 1
                answered_correct += 1
        plain_ok += (com.decide_plain(probe) == label)
        for i, m in enumerate(members):
            single_ok[i] += (m.vote(probe)[0] == label)
    return {
        "accuracy": correct / n,            # refusals count as misses
        "refusal_rate": refused / n,
        "accuracy_on_answered": (answered_correct / answered
                                 if answered else float("nan")),
        "plain_accuracy": plain_ok / n,
        "best_single": max(single_ok) / n,
        "n_answered": answered,
    }


def main():
    com, reports = build_committee()
    print("== calibration (sigma=0.25, 200 labeled probes each) ==")
    print(f"  {'member':>6} {'tau':>6} {'J':>6} "
          f"{'acc-in':>7} {'acc-ood':>8}")
    for (name, _), r in zip(MEMBERS, reports):
        print(f"  {name:>6} {r['tau']:>6.3f} {r['J']:>6.3f} "
              f"{r['cal_accept_in']:>7.3f} {r['cal_accept_ood']:>8.3f}")

    print("\n== evaluation on fresh seeds (200 trials each) ==")
    print(f"  {'sigma':>5} {'plain':>6} {'ref-acc':>8} {'ref-rate':>9} "
          f"{'acc-ans':>8} {'best-1':>7}")
    rows = {}
    for sigma in (0.25, 0.50):
        m = evaluate(com, sigma)
        rows[sigma] = m
        tag = " (shift)" if sigma == 0.50 else ""
        print(f"  {sigma:>5.2f} {m['plain_accuracy']:>6.3f} "
              f"{m['accuracy']:>8.3f} {m['refusal_rate']:>9.3f} "
              f"{m['accuracy_on_answered']:>8.3f} {m['best_single']:>7.3f}"
              f"{tag}")

    r25, r50 = rows[0.25], rows[0.50]
    print("\n== the question: does refusal fix the committee? ==")
    print(f"  sigma=0.25: refusing {r25['accuracy']:.3f} vs plain "
          f"{r25['plain_accuracy']:.3f} vs best-single "
          f"{r25['best_single']:.3f}")
    print(f"  sigma=0.50: refusing {r50['accuracy']:.3f} vs plain "
          f"{r50['plain_accuracy']:.3f} vs best-single "
          f"{r50['best_single']:.3f} "
          f"(refusal rate {r50['refusal_rate']:.3f})")
    if r25["accuracy"] > r25["best_single"]:
        print("  VERDICT: yes -- refusal lifts the committee above the "
              "best single member in-distribution.")
    elif r25["accuracy"] > r25["plain_accuracy"]:
        print("  VERDICT: partial -- refusal helps vs the plain "
              "committee but does not reach the best single member.")
    else:
        print("  VERDICT: no -- refusal does not fix the committee's "
              "failure; the aggregation problem stands.")


if __name__ == "__main__":
    main()
