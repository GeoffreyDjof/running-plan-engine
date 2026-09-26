# paces.py — Phase 1 VDOT spec (LOCKED)

Status: **IMPLEMENTED on box** (2026-09-26); contract locked with DomainCoach `docs/coaching-rules.md` §3.7 (2026-09-26).  
Code: **not started** until GitHub remote + `models.py` (ArchiPlan). PlanOrch: no cloud agent yet.  
Owner: EngineMoteur.

## Goal

Deterministic VDOT from a race benchmark → `PaceZones` in **seconds/km** for E / M / T / I / R.  
No LLM. No calendar generation. Planner/templates consume paces **only** via `pace_zones`.

## Locked constants (coaching-rules §3.7)

| Constant | Value |
|----------|-------|
| `VDOT_ANCHOR_DISTANCE` | `"5k"` |
| `VDOT_ANCHOR_TIME_SEC` | `1200` (20:00) |
| `VDOT_ANCHOR_EXPECTED` | `51.0` |
| `VDOT_TOLERANCE_ABS` | `0.5` → `abs(calc - 51.0) ≤ 0.5` |
| `PACE_ZONES_REQUIRED` | `["E","M","T","I","R"]` |
| `PACE_ZONE_METHOD` | `"daniels_vdot_tables"` (Daniels Running Formula; no homemade %VO2) |
| `PACE_OUTPUT_UNIT` | `"sec_per_km"` |

### `BENCHMARK_IMPLAUSIBLE` bounds (seconds)

| Distance | Min (too fast) | Max (too slow) |
|----------|----------------|----------------|
| 5k | `750` (12:30) | `3600` (60:00) |
| 10k | `1560` | `7200` |
| half | `3480` | `14400` |
| marathon | `7500` (2:05) | `28800` (8:00) |

Out of range → raise typed `EngineError` with `code="BENCHMARK_IMPLAUSIBLE"` (no VDOT computed).

### Zone order (sec/km, larger = slower)

`E > M > T > I` and `I >= R`.

### Rounding (EngineMoteur choice; DomainCoach validates contract)

- Store each zone as **nearest integer** seconds/km (`round` half away from zero / Python3 banker's note: use `int(x + 0.5)` for non-neg or `decimal` ROUND_HALF_UP).
- Document choice in module docstring + ADR if changed later.
- VDOT float: keep ≥2 decimal places internally; compare anchor with abs tolerance 0.5.

## Public surface (names final when ArchiPlan ships models)

```python
def vdot_from_benchmark(distance_m: int, time_s: int) -> float: ...
def pace_zones_from_vdot(vdot: float) -> PaceZones: ...
def compute_paces(distance_m: int, time_s: int) -> PaceZones: ...
# or distance key "5k"|"10k"|"half"|"marathon" — match models.PlanRequest
```

Distance mapping for implausible checks must match model distance enums.

## DoD Phase 1

1. Anchor: 5k / 1200 s → VDOT in `[50.5, 51.5]`.
2. Absurd times (table above) → `BENCHMARK_IMPLAUSIBLE`.
3. Zones E/M/T/I/R present, positive ints, order respected.
4. Deterministic: same input → same output.
5. Method = Daniels tables/equations (cite source in docstring).

## Tests (English ids)

See `tests/test_paces_vdot.draft.py` (rename to `test_paces.py` on merge).

## Out of scope

planner, templates, validator, UI, FastAPI, Strava, HF/LLM.
