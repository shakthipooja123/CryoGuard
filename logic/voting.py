"""
CryoGuard — Fail-Safe Sensor Voting
-------------------------------------
Two generalized voting strategies:

1. median_vote()  — for CONTINUOUS parameters (temperature, humidity).
   Takes the median of all readings, flags any sensor whose reading
   deviates from that median beyond `deviation_threshold`, then
   recomputes the trusted value from ONLY the healthy (unflagged)
   sensors. One function serves both temperature and humidity — there
   is nothing parameter-specific about it.

2. quorum_vote()  — for DISCRETE events (jolt / shock detection).
   Shock is a yes/no event per sensor, so instead of measuring
   deviation from a median, CryoGuard asks "did a majority of sensors
   agree a shock occurred?" A confirmed shock requires a quorum of
   sensors (default: >=50%) to report True.
"""

from __future__ import annotations
import statistics
from dataclasses import dataclass
from typing import List


@dataclass
class VoteResult:
    trusted_value: float
    healthy_indices: List[int]
    flagged_indices: List[int]
    raw_median: float


def median_vote(readings: List[float], deviation_threshold: float) -> VoteResult:
    """
    Generalized fail-safe voting for continuous sensor arrays.

    1. Compute the median of all raw readings.
    2. Any sensor whose reading differs from that median by more than
       `deviation_threshold` is flagged as unhealthy.
    3. The trusted value is recomputed as the median of only the
       healthy sensors.
    4. If every sensor disagrees wildly (no healthy sensors survive),
       fall back to the raw median across all sensors so the system
       degrades gracefully instead of returning nothing.
    """
    if not readings:
        return VoteResult(trusted_value=float("nan"), healthy_indices=[], flagged_indices=[], raw_median=float("nan"))

    raw_median = statistics.median(readings)
    healthy, flagged = [], []

    for i, r in enumerate(readings):
        if abs(r - raw_median) <= deviation_threshold:
            healthy.append(i)
        else:
            flagged.append(i)

    if healthy:
        trusted = statistics.median([readings[i] for i in healthy])
    else:
        trusted = raw_median  # graceful degradation — all sensors disagree

    return VoteResult(trusted_value=trusted, healthy_indices=healthy, flagged_indices=flagged, raw_median=raw_median)


@dataclass
class QuorumResult:
    confirmed: bool
    votes_for: int
    total_sensors: int
    agreeing_indices: List[int]


def quorum_vote(shock_flags: List[bool], quorum_fraction: float = 0.5) -> QuorumResult:
    """
    Generalized fail-safe voting for discrete sensor events (jolt/shock).

    A shock event is CONFIRMED only if the fraction of sensors reporting
    True meets or exceeds `quorum_fraction` (default: simple majority).
    A single noisy accelerometer spiking on its own cannot trigger a
    false shock lockout.
    """
    total = len(shock_flags)
    if total == 0:
        return QuorumResult(confirmed=False, votes_for=0, total_sensors=0, agreeing_indices=[])

    agreeing = [i for i, f in enumerate(shock_flags) if f]
    votes = len(agreeing)
    confirmed = (votes / total) >= quorum_fraction

    return QuorumResult(confirmed=confirmed, votes_for=votes, total_sensors=total, agreeing_indices=agreeing)
