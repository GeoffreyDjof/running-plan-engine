# Règles de coaching — running-plan-engine

Version: 2026-09-26  
Source: `docs/handoff.md` (extrait phase 0–1) + arbitrage DomainCoach  
Langue: FR métier / EN constantes & codes  
Principe directeur: **sécurité > personnalisation** ; en cas de doute, plus conservateur.

Ce document est la source de vérité métier pour le validateur et le planner.  
Toute règle nouvelle ou tout changement de constante → ADR dans `docs/decisions.md` + relecture DomainCoach avant merge.

---

## 1. Portée v1

| Inclus | Exclu v1 |
|--------|----------|
| Distances: `5k`, `10k`, `half`, `marathon` | Trail, ultra, piste pure |
| Unités: km, minutes | Miles comme unité primaire |
| Force courte optionnelle (`strength`) | Musculation avancée, périodisation force |
| Polarisation souple (Daniels/Gilbert VDOT) | Copie de plans élite (Pfitz etc.) |
| Kinds listés §2 | Nutrition, GPS/Strava import |

Levels: `beginner` | `intermediate` | `advanced`  
Phases: `base` | `development` | `specific` | `taper` | `race`

---

## 2. Kinds autorisés (v1)

```
rest | easy | long | strides | tempo | cruise_intervals |
intervals | reps | race_pace | recovery | strength | cross
```

### Classes d’intensité (pour les règles)

| Classe | Kinds | Notes |
|--------|-------|-------|
| `EASY_FAMILY` | `easy`, `recovery`, `long` (portion easy), `cross` aérobie | Compte dans le % easy |
| `QUALITY_HARD` | `intervals`, `reps` | « Très-qualité » |
| `QUALITY_TEMPO` | `tempo`, `cruise_intervals`, `race_pace` | Qualité soutenue |
| `NEUROMUSCULAR_LIGHT` | `strides` | Autorisé beginner ; pas « très-qualité » |
| `STRENGTH` | `strength` | Court, optionnel ; hors volume course |
| `REST` | `rest` | |

**Beginner v1** : pas de `QUALITY_HARD` (`intervals`, `reps`). `strides` OK. `QUALITY_TEMPO` plafonné (voir §5).

---

## 3. Constantes nommées

### 3.1 Progression volume

| Constante | Valeur | Sens |
|-----------|--------|------|
| `TARGET_WEEKLY_INCREASE_MIN` | `0.05` | Hausse cible basse entre semaines de charge |
| `TARGET_WEEKLY_INCREASE_MAX` | `0.10` | Hausse cible haute (planner vise ici) |
| `MAX_WEEKLY_INCREASE` | `0.10` | Alias métier = `TARGET_WEEKLY_INCREASE_MAX` |
| `MAX_WEEKLY_INCREASE_HARD` | `0.12` | **Fail validateur** si Δ vs dernière semaine de **charge** > cette valeur (ADR-005) |
| `NO_CONSECUTIVE_LARGE_INCREASE_THRESHOLD` | `0.10` | Jamais 2 hausses consécutives de charge si la précédente > ce seuil |
| `DELOAD_FRACTION_MIN` | `0.70` | Semaine `is_deload=true` ≥ 70 % du pic de charge récent |
| `DELOAD_FRACTION_MAX` | `0.80` | Semaine `is_deload=true` ≤ 80 % du pic de charge récent |
| `DELOAD_EVERY_WEEKS_MIN` | `3` | Deload au plus tôt toutes les 3 sem de charge |
| `DELOAD_EVERY_WEEKS_MAX` | `4` | Deload au plus tard toutes les 4 sem de charge |

**Mesure R01 (ADR-005)** : le Δ volume se calcule vs la **dernière semaine de charge** (`is_deload=false`), jamais vs une deload. Le rebond deload→charge n’est pas un fail R01 en soi.

Exception documentée à `MAX_WEEKLY_INCREASE_HARD` (hors ADR-005) : uniquement reprise post-blessure / retour de coupure **avec** `injury.active=false` et note moteur explicite — sinon fail `VALIDATION_FAILED`.

**R04** : toute semaine `is_deload=true` doit être dans `[DELOAD_FRACTION_MIN, DELOAD_FRACTION_MAX]` du pic de charge récent (sinon `VALIDATION_FAILED` / rule_id deload).

Volume de départ planner : `start_weekly_km = median(recent_weekly_km)` borné par les plafonds §4 et par `VOLUME_TOO_LOW_FOR_GOAL` si trop bas pour l’objectif.

### 3.2 Polarisation / intensité

| Constante | Valeur | Sens |
|-----------|--------|------|
| `EASY_SHARE_MIN_LOAD_WEEK` | `0.75` | % minutes (ou km) `EASY_FAMILY` sur semaine de **charge** (hors taper/race) |
| `EASY_SHARE_TARGET` | `0.80` | Cible planner ; validateur refuse si < `EASY_SHARE_MIN_LOAD_WEEK` |
| `MAX_VERY_HARD_QUALITY_PER_WEEK` | `1` | Max séances `QUALITY_HARD` / semaine |
| `MAX_TEMPO_QUALITY_PER_WEEK` | `1` | Max séances `QUALITY_TEMPO` / semaine |
| `FORBID_HARD_QUALITY_CONSECUTIVE_DAYS` | `true` | Pas `QUALITY_HARD` ni `QUALITY_TEMPO` en J et J+1 |
| `DAY_AFTER_LONG_ALLOWED` | `["easy", "recovery", "rest"]` | Lendemain de `long` uniquement ces kinds |

Sur semaine **taper** / **race** : le seuil easy peut descendre (course = qualité) ; le validateur n’applique pas `EASY_SHARE_MIN_LOAD_WEEK` ces semaines, mais conserve l’interdiction qualité dure J/J+1 et les plafonds de séance.

### 3.3 Long run

| Constante | Valeur | Sens |
|-----------|--------|------|
| `LONG_RUN_SHARE_MAX_BEGINNER` | `0.35` | `long` ≤ 35 % du volume hebdo (km) |
| `LONG_RUN_SHARE_MAX_INTERMEDIATE` | `0.38` | ≤ 38 % |
| `LONG_RUN_SHARE_MAX_ADVANCED` | `0.40` | ≤ 40 % |
| `LONG_RUN_ON_MAX_MINUTES_DAY` | `true` | Placer le long sur le jour avec le plus grand `max_minutes` dispo |

Fail si `long_km / week_km > LONG_RUN_SHARE_MAX_*` pour le level.

### 3.4 Durée de séance

| Constante | Valeur | Sens |
|-----------|--------|------|
| `SESSION_MUST_RESPECT_MAX_MINUTES` | `true` | `total_minutes_est ≤ availability.max_minutes` du jour |
| `STRENGTH_MAX_MINUTES` | `30` | Plafond force courte v1 |
| `BEGINNER_QUALITY_TEMPO_MAX_PER_PLAN` | `1` | Beginner : au plus une séance tempo-like par semaine de specific, sinon easy/strides |

### 3.5 Taper (jours avant course)

| Objectif | Constante | Jours |
|----------|-----------|-------|
| 5k | `TAPER_DAYS_5K_MIN` / `_MAX` | `7` / `10` |
| 10k | `TAPER_DAYS_10K_MIN` / `_MAX` | `7` / `10` |
| Semi | `TAPER_DAYS_HALF_MIN` / `_MAX` | `10` / `14` |
| Marathon | `TAPER_DAYS_MARATHON_MIN` / `_MAX` | `14` / `21` |

Si une course (`race` ou date objectif) est dans le plan : une phase `taper` d’une durée dans la fourchette **doit** exister. Sinon fail `VALIDATION_FAILED` (taper manquant).

### 3.6 Blessure (`injury`)

| Constante | Valeur | Sens |
|-----------|--------|------|
| `INJURY_BLOCKS_QUALITY_HARD` | `true` | `intervals` / `reps` → erreur `INJURY_BLOCKS_QUALITY` |
| `INJURY_BLOCKS_QUALITY_TEMPO` | `true` | `tempo` / `cruise_intervals` / `race_pace` bloqués si injury récente active |
| `INJURY_LONG_RUN_SHARE_CAP` | `0.30` | Plafond long sous injury (tous levels) |
| `INJURY_PREFER_TIME_BASED_EASY` | `true` | Easy en minutes, pas km agressifs |
| `INJURY_EMIT_WARNING` | `true` | Warning métier obligatoire sur le plan |

Pas de diagnostic inventé : le moteur lit le flag input ; il ne diagnostique pas.

### 3.7 VDOT / allures (contrat paces — détail EngineMoteur)

Ancre Phase 1 (handoff) : **5k en `20:00` → VDOT ≈ `51`**.

| Constante | Valeur | Sens |
|-----------|--------|------|
| `VDOT_ANCHOR_DISTANCE` | `"5k"` | Distance de référence test |
| `VDOT_ANCHOR_TIME_SEC` | `1200` | 20:00 |
| `VDOT_ANCHOR_EXPECTED` | `51.0` | VDOT attendu |
| `VDOT_TOLERANCE_ABS` | `0.5` | `abs(VDOT_calc - 51) ≤ 0.5` pour l’ancre |
| `PACE_ZONES_REQUIRED` | `["E","M","T","I","R"]` | Zones Daniels, sortie en **secondes/km** |
| `PACE_ZONE_METHOD` | `"daniels_vdot_tables"` | Équations/tables Daniels Running Formula (pas %VO2 inventé) |
| `PACE_OUTPUT_UNIT` | `"sec_per_km"` | Unité unique dans `pace_zones` |

#### Bornes `BENCHMARK_IMPLAUSIBLE` (temps de course input)

Temps hors bornes → erreur `BENCHMARK_IMPLAUSIBLE` (pas de VDOT calculé).

| Distance | Min (trop rapide) | Max (trop lent) |
|----------|-------------------|-----------------|
| 5k | `BENCHMARK_5K_MIN_SEC` = `750` (12:30) | `BENCHMARK_5K_MAX_SEC` = `3600` (60:00) |
| 10k | `BENCHMARK_10K_MIN_SEC` = `1560` (26:00) | `BENCHMARK_10K_MAX_SEC` = `7200` (2:00:00) |
| half | `BENCHMARK_HALF_MIN_SEC` = `3480` (58:00) | `BENCHMARK_HALF_MAX_SEC` = `14400` (4:00:00) |
| marathon | `BENCHMARK_MARATHON_MIN_SEC` = `7500` (2:05:00) | `BENCHMARK_MARATHON_MAX_SEC` = `28800` (8:00:00) |

Rationale : min sous l’élite extrême pour une asso ; max au-delà d’un benchmark de course crédible pour prescription VDOT.

#### Contrat zones E / M / T / I / R

1. Calculer `vdot` depuis le benchmark (formule Daniels standard).
2. Dériver les cinq allures via **tables/équations Daniels Running Formula** — pas un barème %VO2 maison.
3. Stocker dans `pace_zones` : `{ "E", "M", "T", "I", "R" }` en **secondes/km** (arrondi documenté dans `docs/paces-vdot-spec.md`).
4. Ordre obligatoire (sec/km, plus grand = plus lent) : `E > M > T > I` et `I >= R` (R le plus rapide ou égal à I).

Owner d’implémentation + fixtures numériques : EngineMoteur (`docs/paces-vdot-spec.md`). DomainCoach valide le contrat, pas le code.

Allures des séances **uniquement** depuis `pace_zones` (secondes/km). Jamais de pace libre hors zones.

---

## 4. Plafonds pic volume (km/semaine)

Garde-fous v1. Le planner ne dépasse pas le **haut** de la fourchette.  
Le validateur **fail** si `peak_weekly_km > PEAK_WEEKLY_KM_MAX[distance][level]`.

Valeurs retenues (conservatrices asso — haut de fourchette handoff) :

| Constante | 5k | 10k | half | marathon |
|-----------|----|-----|------|----------|
| `PEAK_WEEKLY_KM_MAX_BEGINNER` | `35` | `40` | `45` | `50` |
| `PEAK_WEEKLY_KM_MAX_INTERMEDIATE` | `50` | `60` | `65` | `75` |
| `PEAK_WEEKLY_KM_MAX_ADVANCED` | `70` | `80` | `90` | `110` |

Fourchettes handoff (référence, bas → haut) :

| Objectif | Beg | Int | Adv |
|----------|-----|-----|-----|
| 5k | 25–35 | 35–50 | 50–70 |
| 10k | 30–40 | 40–60 | 55–80 |
| Semi | 35–45 | 45–65 | 60–90 |
| Marathon | 40–50 | 55–75 | 70–110 |

`PEAK_WEEKLY_KM_MIN` (bas de fourchette) sert au warning / `VOLUME_TOO_LOW_FOR_GOAL` si le volume de départ ne peut pas monter raisonnablement vers une préparation crédible avant la date.

**À confirmer humain** : si les plafonds asso sont plus bas que ce tableau, abaisser les `PEAK_WEEKLY_KM_MAX_*` (ne pas supprimer les catégories distance×level).

---

## 5. Règles exécutables (pseudo-contrat validateur)

Chaque règle a un **code** d’échec attendu.

| ID | Règle | Code |
|----|-------|------|
| R01 | `week_n.km` (charge) > `last_load_week.km * (1 + MAX_WEEKLY_INCREASE_HARD)` — Δ vs dernière charge, pas vs deload (ADR-005) | `VALIDATION_FAILED` |
| R02 | Deux hausses consécutives de **charge** avec la 1ʳᵉ > `NO_CONSECUTIVE_LARGE_INCREASE_THRESHOLD` | `VALIDATION_FAILED` |
| R03 | Semaine de charge sans deload depuis > `DELOAD_EVERY_WEEKS_MAX` semaines | `VALIDATION_FAILED` |
| R04 | Semaine `is_deload=true` hors `[DELOAD_FRACTION_MIN, DELOAD_FRACTION_MAX]` du pic de charge récent | `VALIDATION_FAILED` |
| R05 | Semaine charge : easy_share < `EASY_SHARE_MIN_LOAD_WEEK` | `VALIDATION_FAILED` |
| R06 | > `MAX_VERY_HARD_QUALITY_PER_WEEK` séances `QUALITY_HARD` | `VALIDATION_FAILED` |
| R07 | > `MAX_TEMPO_QUALITY_PER_WEEK` séances `QUALITY_TEMPO` | `VALIDATION_FAILED` |
| R08 | `QUALITY_HARD` ou `QUALITY_TEMPO` sur jours consécutifs | `VALIDATION_FAILED` |
| R09 | Jour suivant un `long` ∉ `DAY_AFTER_LONG_ALLOWED` | `VALIDATION_FAILED` |
| R10 | `long` share > plafond level (§3.3) | `VALIDATION_FAILED` |
| R11 | Séance `total_minutes_est` > `max_minutes` du jour | `VALIDATION_FAILED` |
| R12 | `level=beginner` + kind ∈ `QUALITY_HARD` | `VALIDATION_FAILED` |
| R13 | `injury.active` + kind qualité bloquée (§3.6) | `INJURY_BLOCKS_QUALITY` |
| R14 | Course dans le plan sans phase `taper` dans la fourchette distance | `VALIDATION_FAILED` |
| R15 | `peak_weekly_km` > plafond distance×level (§4) | `VALIDATION_FAILED` |
| R16 | Pace hors `pace_zones` | `VALIDATION_FAILED` |
| R17 | Benchmark absurde | `BENCHMARK_IMPLAUSIBLE` |
| R18 | `sessions_per_week` incompatible avec `availability` | `INSUFFICIENT_AVAILABILITY` |
| R19 | Objectif trop proche pour construire un plan sûr | `GOAL_TOO_SOON` |
| R20 | Volume de départ trop bas pour l’objectif | `VOLUME_TOO_LOW_FOR_GOAL` |

---

## 6. Cas métier validateur (pass / fail)

Fixtures attendues sous `tests/fixtures/` (noms EN).  
EngineValid colle les seuils **1:1** sur ces constantes.

### 6.1 Doivent PASSER (`valid_*.json`)

| ID | Cas | Attendu |
|----|-----|---------|
| P01 | `valid_plan.json` — 10k intermediate, 4 séances/sem, 12 sem, polarisé, deload S4/S8, taper 7–10j | PASS |
| P02 | Beginner 10k, volume bas, strides + easy only, long ≤ 35 % | PASS |
| P03 | Intermediate half, long ≤ 38 %, lendemain long = easy | PASS |
| P04 | Semaine taper 10k : easy_share peut < 0.75 si race_pace présent, mais pas qualité J/J+1 | PASS |
| P05 | Deload à 75 % du pic après 3 sem de charge (+8 %, +9 %, +7 %) | PASS |
| P06 | Injury active : easy time-based + strength courte, long ≤ 30 %, warning présent | PASS |
| P07 | Advanced 5k, 1× intervals + 1× tempo max, jours non consécutifs, easy ≥ 75 % | PASS |

### 6.2 Doivent ÉCHOUER (`unsafe_*.json`)

| ID | Fixture suggérée | Violation | Code |
|----|------------------|-----------|------|
| F01 | `unsafe_quality_back_to_back.json` | intervals lundi + tempo mardi | `VALIDATION_FAILED` (R08) |
| F02 | `unsafe_long_run_share.json` | intermediate long = 45 % week | `VALIDATION_FAILED` (R10) |
| F03 | `unsafe_weekly_jump.json` | +15 % week-to-week | `VALIDATION_FAILED` (R01) |
| F04 | `unsafe_session_over_max_minutes.json` | séance 100 min, max_minutes=75 | `VALIDATION_FAILED` (R11) |
| F05 | `unsafe_beginner_reps.json` | beginner + reps | `VALIDATION_FAILED` (R12) |
| F06 | `unsafe_injury_intervals.json` | injury.active + intervals | `INJURY_BLOCKS_QUALITY` (R13) |
| F07 | `unsafe_easy_share_low.json` | charge week easy = 60 % | `VALIDATION_FAILED` (R05) |
| F08 | `unsafe_missing_taper.json` | race dans plan, pas de taper | `VALIDATION_FAILED` (R14) |
| F09 | `unsafe_day_after_long.json` | long samedi + intervals dimanche | `VALIDATION_FAILED` (R09) |
| F10 | `unsafe_two_hard_qualities.json` | 2× intervals même semaine | `VALIDATION_FAILED` (R06) |
| F11 | `unsafe_peak_volume.json` | beginner marathon peak 70 km/sem | `VALIDATION_FAILED` (R15) |
| F12 | `unsafe_consecutive_large_increases.json` | +11 % puis +9 % | `VALIDATION_FAILED` (R02) |
| F13 | `unsafe_no_deload.json` | 5 sem charge sans deload | `VALIDATION_FAILED` (R03) |
| F14 | `unsafe_benchmark_implausible.json` | 5k en 8:00 | `BENCHMARK_IMPLAUSIBLE` (R17) |

### 6.3 Critères d’acceptation globaux (rappel QA)

- Plan 10k intermediate 4× / ~12 sem généré → passe validateur.
- Beginner bas volume + objectif marathon → **finisher conservateur** ou erreur claire (`GOAL_TOO_SOON` / `VOLUME_TOO_LOW_FOR_GOAL`) — **jamais** 70 km en semaine 4.
- Messages d’erreur impossibles / métier en français clair côté API plus tard ; codes EN stables.

---

## 7. Structure séance (contrat planner)

- Toute séance course (hors `rest`) : échauffement + corps + retour au calme (`WU` + body + `CD`).
- `notes_fr` : consignes claires pour l’asso (allure relative à la zone, RPE si besoin).
- `total_minutes_est` cohérent avec les splits.
- `strength` : ≤ `STRENGTH_MAX_MINUTES`, hors calcul du % easy course.

---

## 8. Ce que DomainCoach ne fait pas

- N’implémente pas le planner ni le validateur.
- Ne génère pas de calendrier via LLM.
- Ne copie pas un plan élite internet tel quel.
- N’ajoute pas nutrition / trail / muscu avancée en v1.
- Peut **ajuster** les valeurs de constantes ; ne **supprime** pas les catégories (distance×level, kinds, phases).

---

## 9. Changelog arbitrage DomainCoach (vs handoff brut)

| Sujet | Handoff | Décision v1 |
|-------|---------|-------------|
| Hausse hebdo | +5–10 % ; fail évoqué +12 % | `MAX_WEEKLY_INCREASE=0.10` ; hard fail `0.12` |
| Easy share | ≥75–80 % | min validateur `0.75` ; cible `0.80` |
| Long % | ≤35–40 % selon level | 0.35 / 0.38 / 0.40 |
| Plafonds pic | fourchettes | max = haut de fourchette (Geoffrey a gardé le défaut handoff) |
| Beginner | pas reps agressives | interdit tout `QUALITY_HARD` |
| Injury | interdit intervals/reps | étendu aussi à tempo-like + cap long 0.30 |
| VDOT tolérance | ~51 | `VDOT_TOLERANCE_ABS=0.5` |
| Benchmark absurde | non chiffré | bornes min/max par distance (§3.7) |
| Zones | E/M/T/I/R | méthode `daniels_vdot_tables` → sec/km |
| R01 Δ volume | vs semaine précédente | vs dernière semaine de charge (ADR-005) |
| Template 10k int 4× | — | tampon conceptuel 2026-09-26 (S8 deload 74.3 %, pic 36.6) |

