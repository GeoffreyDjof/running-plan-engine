# Draft template — 10k intermediate 4× / 11 sem

Path code : `src/plan_engine/templates/intermediate_10k_4x.py` + `src/plan_engine/planner.py`  
Exemple input : `examples/intermediate_10k.json`  
Owner : EngineMoteur — relecture DomainCoach + veto EngineValid.

## DoD check (box)

- `pytest tests/test_planner_10k.py` : generate_plan → Plan + `validate_plan` OK
- Ancre paces inchangée (Phase 1)
- Pas de push (pas de remote)

## Critères DomainCoach

| Critère | Cible | Statut générateur |
|---------|-------|-------------------|
| easy ≥ 0.75 load weeks | ≥0.75 | validateur OK |
| ≤1 hard + ≤1 tempo | oui | 1 qualité / sem load |
| pas qualité J/J+1 | oui | validateur OK |
| long ≤ 38 % | oui | long_share ~30 % |
| deload 3–4 sem | sem 4 et 8 | oui |
| taper 7–10 j | oui | premières séances taper ≥ race−10j |
| pic ≤ 60 km | cible ~52 | pic observé <40 km (conservateur) |

## Notes

- Template v1 **uniquement** intermediate + 10k + 4 séances.
- Course placée sur `goal.race_date` (exemple : samedi pour caler le jour long).
- Volume volontairement sous le plafond int 60 km (asso).

## Fix DomainCoach (2026-09-26)

- S8 deload ramené à **27.2 km** (74.3 % du pic charge 36.6) — dans `[DELOAD_FRACTION_MIN, DELOAD_FRACTION_MAX]`.
- Planner clamp explicite : semaine `is_deload` ≤ `DELOAD_FRACTION_MAX × last_load_km`.
