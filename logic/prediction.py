"""
CryoGuard — Predictive Confidence & Route Viability
-------------------------------------
Deliberately NOT a machine-learning model. This is a transparent,
physics-inspired stress-accumulation heuristic in the same spirit as a
Vaccine Vial Monitor (VVM): cumulative exposure to off-band conditions
consumes a "safe time budget," rather than trying to learn a black-box
function from (nonexistent, hackathon-scale) training data.

Model:
  - A 0-100 "stress" score accumulates while the shipment is in
    WARNING or CRITICAL, and slowly recovers while SAFE.
  - Predictive confidence (%) = 100 - stress.
  - Estimated remaining safe time = cargo profile's max safe-time
    budget, scaled down by the same fraction as the stress score.
  - Route viability compares that estimated safe time against the
    user-supplied remaining transit time.

This keeps every number traceable to a rule a judge (or a compliance
officer) can audit line by line.
"""

from __future__ import annotations
from dataclasses import dataclass

# Stress accumulation / recovery rates, in stress-points per minute.
WARNING_RATE = 2.0
CRITICAL_RATE = 10.0
RECOVERY_RATE = 0.5


def update_stress(previous_stress: float, state: str, minutes_elapsed: float) -> float:
    if minutes_elapsed < 0:
        minutes_elapsed = 0
    if state == "CRITICAL":
        stress = previous_stress + CRITICAL_RATE * minutes_elapsed
    elif state == "WARNING":
        stress = previous_stress + WARNING_RATE * minutes_elapsed
    else:  # SAFE
        stress = previous_stress - RECOVERY_RATE * minutes_elapsed
    return max(0.0, min(100.0, stress))


def predictive_confidence(stress: float) -> float:
    """0-100%. Higher is better."""
    return max(0.0, 100.0 - stress)


def estimated_safe_hours(stress: float, max_safe_hours: float) -> float:
    """Remaining safe-time budget, scaled down by accumulated stress."""
    return max(0.0, max_safe_hours * (1.0 - stress / 100.0))


@dataclass
class RouteResult:
    status: str  # "VIABLE" | "AT RISK" | "NOT VIABLE"
    margin_hours: float


def route_viability(safe_hours_remaining: float, transit_hours_remaining: float) -> RouteResult:
    """
    Compares estimated safe time against remaining transit time.

      NOT VIABLE — safe-time budget will run out before arrival.
      AT RISK    — arrives with a thin margin (<15% buffer).
      VIABLE     — comfortable margin.
    """
    if transit_hours_remaining <= 0:
        return RouteResult(status="DELIVERED", margin_hours=safe_hours_remaining)

    margin = safe_hours_remaining - transit_hours_remaining

    if margin <= 0:
        status = "NOT VIABLE"
    elif margin < transit_hours_remaining * 0.15:
        status = "AT RISK"
    else:
        status = "VIABLE"

    return RouteResult(status=status, margin_hours=margin)
