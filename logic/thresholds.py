"""
CryoGuard — Cargo Threshold Profiles
-------------------------------------
Each cargo mode carries the temperature / humidity / jolt limits and the
maximum uninterrupted "safe time budget" used by the predictive-confidence
model. Values are set to be representative of widely-cited cold-chain
guidance (WHO EPI, AABB, UNOS-style static cold storage). For a real
deployment these should be reviewed against the exact standard your
organization is certified against — they are presented here as sane,
citable hackathon defaults, not clinical advice.
"""

CARGO_PROFILES = {
    "Vaccine": {
        "temp_min": 2.0,
        "temp_max": 8.0,
        "humidity_min": 20.0,
        "humidity_max": 60.0,
        "jolt_threshold_g": 30.0,
        "max_safe_hours": 48.0,
        "critical_lock_minutes": 5,
        "reference": "WHO EPI Cold Chain / PQS E006 (2-8°C storage & transport band)",
    },
    "Blood": {
        "temp_min": 1.0,
        "temp_max": 6.0,
        "humidity_min": 30.0,
        "humidity_max": 70.0,
        "jolt_threshold_g": 40.0,
        "max_safe_hours": 24.0,
        "critical_lock_minutes": 3,
        "reference": "AABB Blood Bank Standards / WHO Blood Cold Chain (1-6°C storage & transport band)",
    },
    "Organ": {
        "temp_min": 4.0,
        "temp_max": 10.0,
        "humidity_min": 30.0,
        "humidity_max": 70.0,
        "jolt_threshold_g": 15.0,
        "max_safe_hours": 8.0,
        "critical_lock_minutes": 2,
        "reference": "UNOS-style static cold storage guidance (4-10°C; low mechanical-shock tolerance, short viability window)",
    },
}

DEFAULT_CARGO_MODE = "Vaccine"

# Number of redundant sensors simulated per continuous parameter (temp / humidity)
# and per discrete parameter (jolt). Kept fixed at 3 so fail-safe voting always
# has a meaningful quorum/median.
NUM_SENSORS = 3
