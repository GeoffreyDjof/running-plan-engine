# Draft templates — 10k beginner 3× + advanced 4×

Owner : EngineMoteur — relecture DomainCoach + veto EngineValid.

## Beginner (`beginner_10k_3x_v1`)

- 3 séances / 11 sem ; peaking **~17 km** (cap 40)
- **Zéro** `QUALITY_HARD` ; qualité = footing + strides (kind `easy` + notes)
- 1× `race_pace` en taper (S10) — `BEGINNER_QUALITY_TEMPO_MAX_PER_PLAN`
- Long ≤ 33 % (plafond level 35 %)
- Deload S4/S8 ≈ 75 % du pic du bloc de charge (R04)
- Exemple : `examples/beginner_10k.json` → `beginner_10k_plan_generated.json`

## Advanced (`advanced_10k_4x_v1`)

- 4 séances / 11 sem ; peaking **~55 km** (cap 80)
- Alternance tempo / intervals ; ≤1 hard + ≤1 tempo / sem
- Long ≤ 38 % (plafond level 40 %)
- Deload S4/S8 ≈ 75 % du pic du bloc
- Exemple : `examples/advanced_10k.json` → `advanced_10k_plan_generated.json`

## Planner

- Dispatcher multi-templates dans `planner.py`
- Clamp long : `long ≤ cap/(1-cap) × other`
- Deload : cible 75 % du **pic du bloc** (reset après deload), aligné R04 validateur

## Statut

- `validate_plan` VERT sur les 3 dumps 10k
- pytest : suite complète à confirmer après ajout tests levels
- En attente tampon DomainCoach + EngineValid avant figeage
