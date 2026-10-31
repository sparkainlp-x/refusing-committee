"""Tests for refusing-committee. Run: python tests.py"""

import math
import random

from rcommittee import (RefusingCommittee, RefusingMember, merge_qubit,
                        normalize, noisy, rand_state)

S2 = 2 ** -0.5
S3 = 3 ** -0.5
S8 = 1.0 / math.sqrt(8)
PATS = [
    [S2, 0j, 0j, 0j, 0j, 0j, 0j, S2],
    [0j, S3, S3, 0j, S3, 0j, 0j, 0j],
    [1, 0j, 0j, 0j, 0j, 0j, 0j, 0j],
    [S8] * 8,
]


def test_merge_qubit_known():
    ghz = [S2, 0j, 0j, 0j, 0j, 0j, 0j, S2]
    m = merge_qubit(ghz, 2)
    assert len(m) == 4
    assert abs(m[0] - S2) < 1e-12 and abs(m[3] - S2) < 1e-12
    assert abs(m[1]) < 1e-12 and abs(m[2]) < 1e-12


def test_member_normalizes_stored_patterns():
    # REGRESSION: the full-resolution member (empty merge set) once
    # skipped normalization, inflating one pattern's overlaps so it
    # won every vote. Stored patterns must be unit norm, always.
    bad = [0.7071] * 8  # norm 2, not 1
    m = RefusingMember("full", set(), [bad, [1] + [0j] * 7])
    for p in m.patterns:
        assert abs(sum(abs(c) ** 2 for c in p) - 1.0) < 1e-12


def test_calibration_deterministic():
    m1 = RefusingMember("full", set(), PATS)
    m2 = RefusingMember("full", set(), PATS)
    r1 = m1.calibrate(sigma=0.25, seed=11)
    r2 = m2.calibrate(sigma=0.25, seed=11)
    assert r1["tau"] == r2["tau"] and r1["J"] == r2["J"]


def test_calibration_depends_on_calibration_seeds():
    # Calibrate/evaluate separation is structural: the frozen tau
    # must actually depend on the calibration data, not be a
    # constant or leak evaluation state.
    taus = set()
    for s in (11, 22, 33):
        m = RefusingMember("mrg0", {0}, PATS)
        taus.add(m.calibrate(sigma=0.25, seed=s)["tau"])
    assert len(taus) > 1


def test_tau_frozen_after_calibration():
    m = RefusingMember("full", set(), PATS)
    m.calibrate(sigma=0.25, seed=11)
    tau = m.tau
    rng = random.Random(99)
    for _ in range(20):
        m.confident_vote(noisy(PATS[0], 0.25, rng))
    assert m.tau == tau


def test_tau_in_unit_interval_and_J_nonneg():
    m = RefusingMember("full", set(), PATS)
    r = m.calibrate(sigma=0.25, seed=11)
    assert 0.0 <= r["tau"] <= 1.0
    assert r["J"] >= 0.0


def test_all_refuse_means_committee_refuses():
    members = [RefusingMember("a", set(), PATS),
               RefusingMember("b", {0}, PATS)]
    for m in members:
        m.tau = 2.0  # impossible gate: always refuse
    com = RefusingCommittee(members)
    status, winner, nv = com.decide(PATS[0])
    assert status == "refuse" and winner is None and nv == 0


def test_only_confident_members_vote():
    # one member forced to always refuse; the majority must be
    # computed over the remaining voter only.
    a = RefusingMember("a", set(), PATS)
    b = RefusingMember("b", set(), PATS)
    a.tau = 2.0   # always refuses
    b.tau = 0.0   # never refuses (gate passes at tau=0)
    com = RefusingCommittee([a, b])
    status, winner, nv = com.decide(PATS[2])
    assert status == "accept" and nv == 1
    assert winner == b.vote(PATS[2])[0]


def test_clean_probe_accepted_unanimously():
    members = [RefusingMember("full", set(), PATS),
               RefusingMember("mrg0", {0}, PATS)]
    for m in members:
        m.calibrate(sigma=0.25, seed=11)
    com = RefusingCommittee(members)
    status, winner, nv = com.decide(PATS[0])
    assert status == "accept" and winner == 0 and nv == 2


def test_pipeline_deterministic_end_to_end():
    # full pipeline twice on the same seeds -> identical metrics
    def run():
        members = [RefusingMember(n, ms, PATS)
                   for n, ms in [("full", set()), ("mrg01", {0, 1})]]
        for i, m in enumerate(members):
            m.calibrate(sigma=0.25, seed=500 + i)
        com = RefusingCommittee(members)
        out = []
        for s in range(30):
            rng = random.Random(7000 + s)
            label = rng.randrange(len(PATS))
            probe = noisy(PATS[label], 0.25, rng)
            out.append(com.decide(probe)[:2])
        return out
    assert run() == run()


if __name__ == "__main__":
    tests = sorted((k, v) for k, v in globals().items()
                   if k.startswith("test_"))
    assert len(tests) >= 7, "need at least 7 tests"
    for name, fn in tests:
        fn()
        print(f"PASS {name}")
    print("all tests passed")
