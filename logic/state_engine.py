"""
CryoGuard — State Engine
-------------------------------------
Evaluates the trusted (post-voting) readings against the active cargo
profile and produces one of SAFE / WARNING / CRITICAL, with human-
readable reasons. Also tracks how long the shipment has been
continuously CRITICAL — once that exceeds the cargo profile's
`critical_lock_minutes`, the shipment is LOCKED and requires an
explicit human-override action to continue.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List


@dataclass
class StateResult:
    state: str  # "SAFE" | "WARNING" | "CRITICAL"
    reasons: List[str] = field(default_factory=list)


def evaluate_state(
    trusted_temp: float,
    trusted_humidity: float,
    shock_confirmed: bool,
    battery_pct: float,
    profile: dict,
    warning_margin_fraction: float = 0.15,
) -> StateResult:
    reasons: List[str] = []
    is_critical = False
    is_warning = False

    # --- Temperature ---
    t_min, t_max = profile["temp_min"], profile["temp_max"]
    if trusted_temp < t_min or trusted_temp > t_max:
        is_critical = True
        reasons.append(f"Temperature {trusted_temp:.1f}\u00b0C is outside the safe band ({t_min}-{t_max}\u00b0C).")
    else:
        margin = (t_max - t_min) * warning_margin_fraction
        if trusted_temp < t_min + margin or trusted_temp > t_max - margin:
            is_warning = True
            reasons.append(f"Temperature {trusted_temp:.1f}\u00b0C is nearing the edge of the safe band.")

    # --- Humidity ---
    h_min, h_max = profile["humidity_min"], profile["humidity_max"]
    if trusted_humidity < h_min or trusted_humidity > h_max:
        is_critical = True
        reasons.append(f"Humidity {trusted_humidity:.1f}% is outside the safe band ({h_min}-{h_max}%).")
    else:
        margin = (h_max - h_min) * warning_margin_fraction
        if trusted_humidity < h_min + margin or trusted_humidity > h_max - margin:
            is_warning = True
            reasons.append(f"Humidity {trusted_humidity:.1f}% is nearing the edge of the safe band.")

    # --- Jolt / shock ---
    if shock_confirmed:
        is_critical = True
        reasons.append("Jolt/shock event CONFIRMED by sensor quorum.")

    # --- Battery ---
    if battery_pct <= 10:
        is_critical = True
        reasons.append(f"Battery critically low ({battery_pct:.0f}%).")
    elif battery_pct <= 25:
        is_warning = True
        reasons.append(f"Battery running low ({battery_pct:.0f}%).")

    if is_critical:
        state = "CRITICAL"
    elif is_warning:
        state = "WARNING"
    else:
        state = "SAFE"
        reasons.append("All parameters within safe operating band.")

    return StateResult(state=state, reasons=reasons)


def update_critical_lock(
    current_state: str,
    minutes_elapsed: float,
    critical_streak_minutes: float,
    critical_lock_minutes: float,
    already_locked: bool,
) -> tuple[float, bool]:
    """
    Tracks continuous time spent in CRITICAL. Returns
    (new_critical_streak_minutes, is_locked).

    Any non-CRITICAL reading resets the streak — the lock only trips on
    *sustained* critical conditions, not a single noisy tick.
    Once locked, it stays locked until a human override clears it
    (handled by the caller / UI, not here).
    """
    if already_locked:
        return critical_streak_minutes, True

    if current_state == "CRITICAL":
        critical_streak_minutes += minutes_elapsed
    else:
        critical_streak_minutes = 0.0

    is_locked = critical_streak_minutes >= critical_lock_minutes
    return critical_streak_minutes, is_locked
