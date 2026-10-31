"""The refusing committee: a heterogeneous membrane committee whose
members may refuse to vote.

Fuses two prior builds:
  - membrane-committee: members at different coarse-graining
    resolutions (full 8 amps; merge qubit {0}/{1}/{2} -> 4 amps;
    merge {0,1} -> 2 amps), majority vote. Measured finding: the
    plain committee underperforms the best single member.
  - refusing-membrane: an OES-style gate on max overlap, with the
    threshold tau self-calibrated via Youden's J on labeled probes
    (in-library vs out-of-distribution), then frozen.

Each member calibrates its OWN tau on its OWN view (calibration
seeds are structurally separate from evaluation seeds). The
committee rule: only members with max-overlap >= tau vote;
majority among voters (ties -> highest weight); if ALL refuse,
the committee REFUSES -- reported as its own outcome, not a
wrong answer.

The question: does refusal fix the committee's measured failure?
Whatever the numbers say is the finding, including "no".
"""

import math
import random


# ------------------------------------------------------------ utils
# (copied from hcommittee.py / rmembrane.py -- no cross-package imports)

def normalize(v):
    n = math.sqrt(sum(abs(c) ** 2 for c in v))
    return [c / n for c in v]


def overlap(field, pattern):
    return sum(p.conjugate() * f for p, f in zip(pattern, field))


def noisy(state, sigma, rng):
    return normalize([c + complex(rng.gauss(0, sigma), rng.gauss(0, sigma))
                      for c in state])


def rand_state(n, rng):
    """Haar-random pure state via complex Gaussians (OOD probes)."""
    return normalize([complex(rng.gauss(0, 1), rng.gauss(0, 1))
                      for _ in range(n)])


def merge_qubit(state, q):
    """Haar low-pass merging qubit q: 2^n -> 2^(n-1) amplitudes."""
    s2 = math.sqrt(2.0)
    out = []
    for i in range(len(state)):
        j = i ^ (1 << q)
        if j > i:
            out.append((state[i] + state[j]) / s2)
    return normalize(out)


def merge_qubits(state, qs):
    """Merge a set of *original* qubit indices (order-independent).
    After merging qubit q, higher original qubits shift down by one,
    which the index adjustment handles."""
    for shift, q in enumerate(sorted(set(qs))):
        state = merge_qubit(state, q - shift)
    return state


# ------------------------------------------------------- member
class RefusingMember:
    """One committee member at a fixed resolution, with a calibrated
    refusal gate."""

    def __init__(self, name, merge_set, patterns):
        self.name = name
        self.merge_set = set(merge_set)
        self.raw = list(patterns)
        self.dim = len(patterns[0])
        # normalize AFTER merging: merge_qubit normalizes, but the
        # empty merge set (full resolution) must normalize too --
        # otherwise an unnormalized pattern's overlaps are inflated
        # and it wins every vote (past bug, pinned by regression test).
        self.patterns = [normalize(merge_qubits(p, self.merge_set))
                         for p in patterns]
        self.tau = None

    def _view(self, probe):
        return merge_qubits(probe, self.merge_set)

    def overlaps(self, probe):
        pv = self._view(probe)
        return [overlap(pv, p) for p in self.patterns]

    def max_overlap(self, probe):
        return max(abs(m) for m in self.overlaps(probe))

    def vote(self, probe):
        """Plain vote, ignoring the gate: (winner, weight)."""
        ms = self.overlaps(probe)
        tot = sum(abs(m) ** 2 for m in ms)
        w = max(range(len(ms)), key=lambda i: abs(ms[i]))
        return w, (abs(ms[w]) ** 2 / tot if tot else 0.0)

    def confident_vote(self, probe):
        """(winner, weight) if the gate passes, else None (refuse)."""
        ms = self.overlaps(probe)
        tot = sum(abs(m) ** 2 for m in ms)
        if tot == 0:
            # Zero evidence: orthogonal to the whole stored subspace.
            # Refuse outright -- never argmax over zeros.
            return None
        if self.tau is not None and max(abs(m) for m in ms) < self.tau:
            return None
        w = max(range(len(ms)), key=lambda i: abs(ms[i]))
        return w, abs(ms[w]) ** 2 / tot

    def calibrate(self, sigma=0.25, n_in=100, n_ood=100, seed=0,
                  grid=101):
        """Self-calibrate tau via Youden's J on labeled probes, then
        freeze it. In-library probes: noisy patterns at `sigma`.
        OOD probes: Haar-random states. Returns the calibration
        report. All evaluation must use FRESH seeds."""
        rng = random.Random(seed)
        in_probes = [noisy(self.raw[rng.randrange(len(self.raw))],
                           sigma, rng)
                     for _ in range(n_in)]
        ood_probes = [rand_state(self.dim, rng) for _ in range(n_ood)]
        in_scores = [self.max_overlap(f) for f in in_probes]
        ood_scores = [self.max_overlap(f) for f in ood_probes]
        best = None
        for g in range(grid):
            tau = g / (grid - 1)
            tpr = sum(s >= tau for s in in_scores) / len(in_scores)
            fpr = sum(s >= tau for s in ood_scores) / len(ood_scores)
            if best is None or (tpr - fpr) > best[0]:
                best = (tpr - fpr, tau, tpr, fpr)
        self.tau = best[1]
        return {"tau": best[1], "J": best[0],
                "cal_accept_in": best[2], "cal_accept_ood": best[3]}


# ------------------------------------------------------- committee
class RefusingCommittee:
    def __init__(self, members):
        self.members = members

    @staticmethod
    def _majority(votes):
        tally = {}
        for w, wt in votes:
            tally[w] = tally.get(w, [0, 0.0])
            tally[w][0] += 1
            tally[w][1] = max(tally[w][1], wt)
        return max(tally, key=lambda w: (tally[w][0], tally[w][1]))

    def decide(self, probe):
        """('accept', winner, n_voters) or ('refuse', None, 0).
        Only gate-passing members vote; majority among voters;
        ties -> highest weight; all refuse -> committee refuses."""
        votes = [v for v in (m.confident_vote(probe)
                             for m in self.members) if v is not None]
        if not votes:
            return ("refuse", None, 0)
        return ("accept", self._majority(votes), len(votes))

    def decide_plain(self, probe):
        """Baseline: every member votes, gate ignored."""
        return self._majority([m.vote(probe) for m in self.members])
