# Architecture — running-plan-engine

Version : 2026-10-02 (phase 0 + contrat P0-2)  
Audience : équipe agents + porteur humain  
Source de vérité runtime : **schémas Pydantic / JSON** (`src/plan_engine/models.py`), pas le Markdown.

## 1. Objectif

Moteur **déterministe** de plans d’entraînement pour une association de running (5 km, 10 km, semi, marathon).

- Entrée / sortie : JSON **validé** par contrat Pydantic (§5 handoff).
- Même entrée → même sortie (hors seed d’adaptation explicite, hors scope phase 0–1).
- Le **LLM n’écrit jamais le calendrier** : il explique ou propose une adaptation qui **doit repasser** par le validateur avant d’être acceptée.

## 2. Frontières de modules et ownership

| Module / artefact | Owner | Rôle |
|---|---|---|
| `models.py` | ArchiPlan | Contrats d’interface (PlanRequest, Plan, EngineError) |
| `paces.py` | EngineMoteur | VDOT + zones E/M/T/I/R |
| `templates/` + `planner.py` | EngineMoteur | Motifs de phase → semaines / séances |
| `validator.py` | EngineValid | Garde-fous ; peut **veto** un template agressif |
| `docs/coaching-rules.md` | DomainCoach | Constantes et règles métier |
| `tests/` (+ matrice QA) | QAPlan | Couverture métier |

Fichiers prévus plus tard (hors phase 0–1) : `adapter.py`, `explain.py`, CLI, API HTTP.

## 3. Pipeline

```text
PlanRequest
    → (optionnel) paces  → PaceZones + VDOT / confiance
    → planner            → Plan (brouillon)
    → validator          → Plan OK  |  EngineError
```

- Le validateur peut **refuser** un plan trop agressif (templates inclus).
- On ne renvoie **jamais** un plan invalide : erreur typée `EngineError`.

## 4. Contrat imbriqué (rappel §5)

**Input `PlanRequest`** : `athlete` (profil, `recent_weekly_km` 4 sem. plus récente en dernier, `availability`, `constraints.injuries`) + `benchmark?` (`distance_km`, `time_sec`) + `goal` (`distance_km`, `race_date?`) + `options` (`sessions_per_week`, `units: metric`, `language: fr`, `as_of_date?`).

`options.as_of_date` est la date de référence du calcul (jours-à-course, dates de semaine). **Même input + même `as_of_date` → même JSON.** Absent = le planner choisira sa date de repli (aujourd’hui hardcodé jusqu’à P0-7).

**Output `Plan`** : `meta` (version, VDOT, `paces_confidence`, `as_of_date?`, `generated_at` dérivé/déterministe, `warnings: list[PlanWarning]`) + `pace_zones` (E|M|T|I|R, pace central + `range?`) + `plan` (semaines → séances avec `structure` WU / corps / CD).

`PlanWarning` : `code` (id anglais stable, ex. `START_VOLUME_CAPPED`), `message_fr`, `details` (défaut `{}`). Non bloquant ; un refus reste `EngineError`.

## 5. Erreurs métier typées (`ErrorCode`)

**Uniquement** les 6 codes top-level handoff (§5.3) :

- `INSUFFICIENT_AVAILABILITY`
- `GOAL_TOO_SOON`
- `VOLUME_TOO_LOW_FOR_GOAL`
- `BENCHMARK_IMPLAUSIBLE`
- `INJURY_BLOCKS_QUALITY` — blessure + qualité (intervals / reps) ; pas de code `INJURY_BLOCKS_INTERVALS`
- `VALIDATION_FAILED`

Les **rule ids** validateur (phase 2) ne sont **pas** des valeurs `ErrorCode`. Ils vivent dans `EngineError.details`, typiquement sous `code=VALIDATION_FAILED` (ou `INJURY_BLOCKS_QUALITY` si blessure+qualité) :

```json
{
  "code": "VALIDATION_FAILED",
  "message_fr": "Plan refusé par le validateur.",
  "details": {
    "rule_id": "QUALITY_BACK_TO_BACK",
    "broken_rules": ["QUALITY_BACK_TO_BACK", "INSUFFICIENT_EASY_RATIO"]
  }
}
```

Rule ids connus (non exhaustif, constantes / coaching-rules) : `QUALITY_BACK_TO_BACK`, `LONG_RUN_OVER_CEILING`, `VOLUME_JUMP_TOO_HIGH`, `SESSION_OVER_MAX_MINUTES`, `BEGINNER_AGGRESSIVE_REPS`, `INSUFFICIENT_EASY_RATIO`, `MISSING_TAPER`. Promotion en `ErrorCode` top-level **uniquement via ADR**.

## 5bis. Champs Session / Plan (canoniques)

Aligné handoff §5.2 — **pas d’alias** :

| Zone | Canonique | Interdit / legacy |
|------|-----------|-------------------|
| Volume séance | `Session.total_km`, `Session.total_minutes_est` | `km`, `min`, `distance_km` sur Session |
| Semaines | `Plan.plan: list[WeekPlan]` | clé top-level `weeks` (sauf `meta.weeks: int`) |
| Allures | `PaceZones.E…R` → `PaceZoneDetail.pace_sec_per_km` + `label` + `range?` (`PaceRange.min/max_sec_per_km`) | int brut par zone |
| Date de référence | `options.as_of_date?` → echo `meta.as_of_date?` | date système / today hardcodé dans le contrat |
| Horodatage | `meta.generated_at` dérivé / déterministe (pas wall-clock) | `datetime.now()` |
| Warnings | `meta.warnings: list[PlanWarning]` (`code`, `message_fr`, `details`) | `list[str]` |
| Structure | `Session.structure[]` avec `block` / `duration_min` / `distance_km` / `zone` | — |

Le validateur lit **`total_km`** (pas `distance_km` sur Session). `distance_km` n’existe que sur `StructureBlock`.

## 6. Non-goals phases 0–1

Pas de FastAPI / HTTP, pas d’UI, pas de Hugging Face / fine-tune, pas d’import Strava/Garmin, pas de trail / nutrition / musculation avancée.

## 7. Layout repo (aligné handoff)

```text
running-plan-engine/
  README.md, pyproject.toml
  docs/architecture.md, coaching-rules.md, decisions.md, handoff.md
  src/plan_engine/{models,paces,planner,validator,templates}/
  tests/, examples/, scripts/generate_cli.py
```

## 8. Principes

1. Déterminisme et schéma JSON avant tout livrable UI.
2. Sécurité > personnalisation ; constantes dans `coaching-rules.md`.
3. Markdown = documentation humaine ; le runtime ne parse pas le Markdown pour générer un plan.
