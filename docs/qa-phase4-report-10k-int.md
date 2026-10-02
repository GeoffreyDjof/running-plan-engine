# Rapport QA phase 4 — ACC-01 / HP-10k-int-s4-inj0

> **Archive (2026-09-26).** Le décompte « 38 tests » et le blocage « template `intermediate_10k_4x` seul » sont **obsolètes**. Rapport consolidé à jour (48 tests sur `main` @ 4139b77, table P0) : [`qa-phase4-report.md`](qa-phase4-report.md). Ce fichier est conservé comme preuve ACC-01 du 26 sept.

> Date : 2026-09-26 (Europe/Paris)  
> Owner : QAPlan (exécuteur BOX ONLY)  
> Input : `examples/intermediate_10k.json`  
> Artifact : `examples/intermediate_10k_plan_generated.json`  
> Verdict : **VERT**

---

## 1. Verdict

| ID | Case | Verdict | Note |
|----|------|---------|------|
| ACC-01 | Plan 10k intermediate 4 séances / ~12 sem généré + validé | **VERT** | Fixture course → **11 sem** (fenêtre 2026-09-28 → 2026-12-12 ≈ 10,7 sem) — aligné template + tests (`meta.weeks == 11`) |
| HP-10k-int-s4-inj0 | Happy path matrice §2 #1 | **VERT** | Voir preuves §3 |

---

## 2. Pytest

```
.venv/bin/pytest -q
......................................  [100%]
38 passed in ~0.10s
```

| Fichier | Rôle |
|---------|------|
| `tests/test_paces.py` | VDOT / pace_zones |
| `tests/test_models_examples.py` | exemples Pydantic |
| `tests/test_validator.py` | valid_plan + 15 unsafe_* |
| `tests/test_planner_10k.py` | generate + validate + artifact canonique + INSUFFICIENT_AVAILABILITY |

Échecs : **0**.

---

## 3. Preuves happy path

| Critère | Observé |
|---------|---------|
| `distance` | goal `10.0` km |
| `level` | `intermediate` |
| `sessions_per_week` (options) | `4` |
| `injury` | `constraints.injuries == []` |
| `meta.weeks` / `len(plan)` | **11** / **11** |
| Séances / sem (obs.) | `[4,4,4,4,4,4,4,4,4,3,2]` (taper/race) |
| `validate_plan` | **ok = True**, `errors = []` |
| Allures | uniquement refs zones `E`/`T`/`I` dans `structure[].zone` ; **0** champ `pace_sec*` hors `pace_zones` |
| `pace_zones` | E=365, M=304, T=287, I=263, R=245 s/km |
| Déterminisme | `generate_plan` ×2 → JSON identique ; artifact == live (byte-stable via `model_dump`) |
| Artifact stale ? | **Non** — régénération live ≡ `intermediate_10k_plan_generated.json` |
| CLI `scripts/generate_cli.py` | **Absent** — vérif via API `plan_engine.planner.generate_plan` |

---

## 4. Matrice — promotion

Cas **HP-10k-int-s4-inj0** promu **VERT** dans `docs/qa-matrix-draft.md` (§2 + ACC-01).  
Prérequis §0 mis à jour (paces / validator / planner / fixtures **PRÉSENTS**).

---

## 5. Blocages restants (reste de la matrice)

| Blocage | Impact |
|---------|--------|
| Templates planner **hors** `intermediate_10k_4x` uniquement | HP 5k / half / marathon / beg / adv / inj1 / s3–s6 → pas encore générables |
| Pas de fixtures input pour les 23 autres HP | Exécution rouge/vert non démarrable |
| Cas ERR-* (E1–E18) partiellement couverts via `unsafe_*` validator ; pas tous branchés sur `generate_plan` | E1 partiel (`test_insufficient_availability`) ; E3–E6, E8, etc. ouverts |
| `scripts/generate_cli.py` manquant | Snapshots manuels via Python seulement |
| Cible matrice « 12 sem » vs fixture 11 sem | Documenté ; pas un ROUGE si fenêtre course < 12 |

Prochaine vague QAPlan : brancher HP-10k-beg / inj1 dès templates EngineMoteur ; promouvoir draft → `docs/qa-matrix.md` après ≥3 HP verts.
