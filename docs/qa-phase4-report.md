# Rapport QA phase 4 — consolidé (`main` @ 4139b77)

> Date : 2026-10-02 (Europe/Paris)
> Owner : QAPlan
> Base vérifiée : `main` @ `4139b77d2df59d4c0b2ef92f6cf2d2d22a61540f` (PR #1, phases 0–3)
> Langue : prose humaine FR ; ids / codes / commandes EN
> Archive ACC-01 (2026-09-26, annonce 38 tests) : [`qa-phase4-report-10k-int.md`](qa-phase4-report-10k-int.md)

---

## 1. Verdict

| ID | Case | Verdict | Note |
|----|------|---------|------|
| Suite pytest | `python3 -m pytest -q` | **48 passed / 0 failed** | Observé sur `4139b77` — l’ancien rapport (38) est obsolète |
| ACC-01 | HP-10k-int-s4-inj0 | **VERT** | Inchangé vs 2026-09-26 (11 sem, artifact stable) |
| Distance × niveau (5k / 10k / half) | 3 × 3 templates v1 | **9/9 VERT** | `generate_plan` + `validate_plan` ok |
| Distance × niveau (marathon) | 3 niveaux | **ROUGE / non générable** | `VALIDATION_FAILED` « Marathon en phase suivante » |
| 12/12 distance × niveau | 4 distances × 3 niveaux | **ne tient pas** | **9/12** (marathon = 3 cellules absentes) |
| ACC-02 | Beginner marathon, sem. 4 ≪ 70 km | **non vérifiable comme plan** | Pas de template marathon ; voir §3.3 |

---

## 2. Pytest — nombre réel sur `main`

Environnement d’exécution (2026-10-02) :

| Outil | Version |
|-------|---------|
| Python | 3.12.3 |
| pydantic | 2.13.5 |
| pytest | 9.1.1 |

Commande (racine du repo, après `pip install -e ".[dev]"`) :

```text
python3 -m pytest -q
................................................                         [100%]
48 passed in 0.15s
```

Collecte : `python3 -m pytest --collect-only -q` → **48 tests collected**.

SHA : `git rev-parse HEAD` = `4139b77d2df59d4c0b2ef92f6cf2d2d22a61540f` (= `origin/main` au moment du run).

| Fichier | Rôle | Tests collectés |
|---------|------|-----------------|
| `tests/test_paces.py` | VDOT / bornes `BENCHMARK_IMPLAUSIBLE` / zones | 13 |
| `tests/test_models_examples.py` | exemples Pydantic + surface `ErrorCode` | 6 |
| `tests/test_validator.py` | `valid_plan` + 15 `unsafe_*` | 16 |
| `tests/test_planner_10k.py` | ACC-01 + `INSUFFICIENT_AVAILABILITY` + artifact | 3 |
| `tests/test_planner_10k_levels.py` | 10k beginner / advanced + dumps | 4 |
| `tests/test_planner_5k.py` | 5k × 3 niveaux | 3 |
| `tests/test_planner_half.py` | half × 3 niveaux + taper 10–14 j | 3 |

Échecs : **0**.

---

## 3. Happy paths recontrôlés le 2026-10-02

Rejeu via `plan_engine.planner.generate_plan` + `validate_plan` (CLI `scripts/generate_cli.py` toujours **absente**).

### 3.1 ACC-01 — HP-10k-int-s4-inj0 — **VERT**

Input : `examples/intermediate_10k.json`
Artifact : `examples/intermediate_10k_plan_generated.json`

| Critère | Observé |
|---------|---------|
| `distance` / `level` / séances | goal `10.0` / `intermediate` / `4` |
| `injury` | `constraints.injuries == []` |
| `meta.weeks` / `len(plan)` | **11** / **11** (fenêtre 2026-09-28 → 2026-12-12) |
| Séances / sem | `[4,4,4,4,4,4,4,4,4,3,2]` (taper / race) |
| `validate_plan` | **ok = True** |
| `pace_zones` (s/km) | E=365, M=304, T=287, I=263, R=245 |
| Déterminisme | `generate_plan` ×2 → JSON identique ; artifact == live |
| `generated_at` | `2026-09-26T09:00:00Z` (**durci** — P0-7 ouvert) |

### 3.2 5k / 10k / half × beginner / intermediate / advanced — **9/9 VERT**

| Cellule | Template | Semaines | Semaine 4 (km, deload) | `validate_plan` |
|---------|----------|----------|------------------------|-----------------|
| 5k beginner | `beginner_5k_3x` | 10 | 10.9 | ok |
| 5k intermediate | `intermediate_5k_4x` | 10 | 20.9 | ok |
| 5k advanced | `advanced_5k_4x` | 10 | 33.5 | ok |
| 10k beginner | `beginner_10k_3x` | 11 | 12.5 | ok |
| 10k intermediate | `intermediate_10k_4x` | 11 | 24.6 | ok |
| 10k advanced | `advanced_10k_4x` | 11 | 37.7 | ok |
| half beginner | `beginner_half_3x` | 12 | 12.5 | ok |
| half intermediate | `intermediate_half_4x` | 12 | 25.3 | ok |
| half advanced | `advanced_half_4x` | 12 | 38.7 | ok |

Note matrice : les ids `HP-*-adv-s5-*` demandent 5 séances ; v1 n’expose que **3× (beginner)** et **4× (intermediate / advanced)**. Les 9 verts correspondent à ces templates, pas aux variantes s5 / s6.

### 3.3 ACC-02 / marathon — **ne tient pas comme happy path**

Tentative (beginner, `goal.distance_km = 42.195`, 3 séances, `recent_weekly_km ≈ 11`) :

```text
EngineError VALIDATION_FAILED
Template v1 disponible: 5k/10k/half beginner 3 séances,
intermediate/advanced 4 séances. Marathon en phase suivante.
```

- Aucun plan marathon n’est produit → **impossible de chiffrer la semaine 4**.
- Le critère « jamais 70 km en semaine 4 » n’est vrai que par **absence de génération**, pas par un plan finisher.
- Garde-fou validateur seul : `tests/fixtures/unsafe_peak_volume.json` + `test_unsafe_fixture_fails_with_expected_code[unsafe_peak_volume]` (`VALIDATION_FAILED` / R15).

**Correction** : ne plus annoncer « 12/12 distance × niveau » ni « ACC-02 marathon beginner semaine 4 bien sous 70 km » comme résultats live. Remplacer par **9/12** + ACC-02 **non vérifiable**.

---

## 4. Statut P0 (avant la démo) — `main` @ 4139b77

Source : backlog « P0 : avant la démo de ce soir ».  
Statuts d’après le dépôt **uniquement** (pas d’hypothèse hors repo).

| # | Item | Statut | Preuve (une ligne) |
|---|------|--------|--------------------|
| P0-1 | Constantes `START_VOLUME_MAX_RATIO` / plancher / seuils `VOLUME_TOO_LOW_FOR_GOAL` distance×niveau / largeur fourchettes E/M/T/I/R | **pas commencé** | `START_VOLUME_MAX_RATIO` absent de `docs/coaching-rules.md` et `src/plan_engine/constants.py` ; cas chiffré « 11 km/sem visant un semi » **absent** |
| P0-2 | `PaceRange {min,max}` ; `as_of_date` injectable ; `meta.warnings` | **partiel** | `PaceRange` et `as_of_date` absents de `models.py` ; pas d’ADR dédié dans `decisions.md` ; `PlanMeta.warnings: list[str]` existe déjà, mais les 9 plans live sortent `warnings=[]` |
| P0-3 | Brancher `validate_plan` à la fin de `generate_plan` | **pas commencé** | `generate_plan` retourne `Plan(...)` sans appeler `validate_plan` (`planner.py`) ; test d’injection invalide → `VALIDATION_FAILED` + `rule_id` **absent** |
| P0-4 | Volume de départ = médiane 4 sem, sans remontée forcée ; `VOLUME_TOO_LOW_FOR_GOAL` atteignable | **pas commencé** | `_peak_km` fait `start = max(lo, min(start, hi))` ; input 11 km/sem half beginner → S1 **16.1 km**, pas d’erreur |
| P0-5 | Validateur : volume S1 ≤ plafond × km réel récent | **pas commencé** | fixture `unsafe_start_volume_above_recent.json` **absente** |
| P0-6 | Allures en fourchettes min–max | **pas commencé** | `PaceZoneDetail.pace_sec_per_km` = point unique ; aucun min < max |
| P0-7 | Supprimer « today » / `generated_at` durcis | **pas commencé** | `generated_at=datetime(2026, 9, 26, 9, 0, tzutc)` dans `planner.py` ; `as_of_date` absent du contrat d’entrée |
| P0-8 | CLI démo `scripts/generate_cli.py` | **pas commencé** | répertoire `scripts/` **absent** ; README sans commande CLI |
| P0-9 | Répétition démo + go/no-go | **prévu ~15h00** | item QA (hors code) |
| P0-10 | Mettre à jour le rapport QA (annonce 38 tests) | **cette PR** | ce fichier + liens dans `qa-matrix-draft.md` |

### Points rouges (risque démo)

1. **P0-1 … P0-8** : non livrés sur `main` (P0-2 seulement partiel via `meta.warnings`).
2. **Marathon** : non générable — le 4ᵉ profil démo P0-9 est « débutant sous-entraîné **visant un semi** » (template half beginner **présent**), pas un marathon.
3. **P0-4** : 11 km/sem sur un semi beginner **remonte** S1 à 16.1 km (plancher), au lieu de plafonner au km réel ou de refuser `VOLUME_TOO_LOW_FOR_GOAL`.
4. **P0-3** : `generate_plan` ne revalide pas le `Plan` qu’il renvoie (les tests appellent `validate_plan` à part).
5. **P0-7** : tous les dumps ont `generated_at = 2026-09-26T09:00:00Z`.

---

## 5. Matrice

Prérequis, compteur pytest et 9 HP verts mis à jour dans [`qa-matrix-draft.md`](qa-matrix-draft.md).  
Le rapport 10k-int du 2026-09-26 n’est **pas** supprimé (archive).

---

## 6. Blocages restants

| Blocage | Impact |
|---------|--------|
| Pas de template marathon | ACC-02 / HP-mar-* non exécutables comme plans |
| Templates figés 3× (beg) / 4× (int+adv) | HP s5 / s6 et HP-10k-beg-s4 encore bloqués |
| Pas de chemin injury dans le planner | HP-*-inj1 ouverts |
| `scripts/generate_cli.py` manquant | Démo manuelle via API Python seulement |
| P0-1 … P0-8 non mergés | Contrat démo (fourchettes, `as_of_date`, plafond km réel) non tenu |

Prochaine action QAPlan : **P0-9** répétition ~15h00 — 4 profils (5k beginner, 10k intermediate, half advanced, half beginner sous-volume) + go/no-go ≤ 10 lignes à PlanOrch.
