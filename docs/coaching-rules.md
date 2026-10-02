# Règles de coaching — running-plan-engine

Version: 2026-10-02 (P0-1 : volume de départ, faisabilité, fourchettes d’allure)  
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

Volume de départ planner : **remplacé par §3.8** (2026-10-02). Plus aucune remontée forcée à un minimum par niveau.

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


### 3.8 Volume de départ et faisabilité de l’objectif (P0-1, 2026-10-02)

Pourquoi : les coureurs surestiment leur niveau, et l’ancien planner remontait le départ à un minimum par niveau (un coureur à 11 km/sem pouvait démarrer vers ~31 km/sem, soit près de ×3). La règle devient : **on part du km réel, jamais d’un minimum théorique**. Si le km réel ne permet pas d’atteindre l’objectif en sécurité, on refuse avec un message clair au lieu de gonfler le plan.

| Constante | Valeur | Sens |
|-----------|--------|------|
| `START_VOLUME_MAX_RATIO` | `1.10` | Semaine 1 ≤ 110 % du km de référence récent |
| `START_VOLUME_FLOOR_KM` | `10.0` | Plancher : km de référence < 10 → refus, **jamais** de remontée à 10 |
| `START_REFERENCE_WINDOW_WEEKS` | `4` | Fenêtre lue dans `recent_weekly_km` (les 4 dernières valeurs, la plus récente en dernier) |
| `START_RECENT_MIN_VALUES_NO_WARNING` | `4` | Moins de 4 valeurs → plan possible mais warning FR dans `meta.warnings` |

**Km de référence** (déterministe) :

```
w = recent_weekly_km[-4:]
ref_km = min( median(w), max(w[-2:]) )      # si len(w) == 1 : ref_km = w[0]
week1_cap_km = round(START_VOLUME_MAX_RATIO * ref_km, 1)
```

Justification :
- `1.10` = la même hausse max que d’une semaine de charge à l’autre (`MAX_WEEKLY_INCREASE`). La semaine 1 est simplement « la semaine suivante » du vécu réel du coureur, donc même règle de progression.
- `median` sur 4 semaines : une semaine exceptionnelle (sortie club, vacances) ne fixe pas le départ.
- `min(…, max(2 dernières))` : si le volume baisse (coupure, gêne, fatigue), on repart du récent, pas d’une moyenne gonflée par l’ancien. `max` des 2 dernières plutôt que la dernière seule pour ne pas punir une semaine de récup isolée.
- Plancher `10 km` : en dessous, 3 séances font < 3,5 km chacune ; c’est un programme course-marche de reprise, hors scope v1.

**Planner** (formule, implémentation EngineMoteur) :

```
week1_km = min( week1_cap_km, template.week1_volume_frac * template.TARGET_PEAK_KM )
peak_km  = min( week1_km / template.week1_volume_frac, TARGET_PEAK_KM, PEAK_WEEKLY_KM_CAP )
```

Les autres semaines suivent les `volume_frac` du template (R01/R02/R04 inchangées). Aucun `max(lo, …)` ni `floor_peak` ne doit relever le volume.

**Faisabilité → `VOLUME_TOO_LOW_FOR_GOAL`** (contrôle avant génération) :

Refus si `recent_weekly_km` est vide, ou si `ref_km < START_VOLUME_FLOOR_KM`, ou si `ref_km < RECENT_KM_MIN_FOR_GOAL[level][distance]` :

| `RECENT_KM_MIN_FOR_GOAL` (km/sem réels) | 5k | 10k | half |
|------------------------------------------|----|-----|------|
| beginner | `10` | `13` | `15` |
| intermediate | `16` | `20` | `20` |
| advanced | `26` | `29` | `29` |

Marathon : hors lot P0 (P2), pas de seuil publié.

Dérivation (pour relire les chiffres) : pic minimal crédible pour finir l’objectif en sécurité `PEAK_MIN_FOR_GOAL_KM`, divisé par ce que le template peut atteindre depuis le km réel (`START_VOLUME_MAX_RATIO / week1_volume_frac` = 1,10/0,70 ≈ 1,57 pour 5k/10k, 1,10/0,68 ≈ 1,62 pour 10k beginner, 1,10/0,62 ≈ 1,77 pour le semi), arrondi au km supérieur.

| `PEAK_MIN_FOR_GOAL_KM` (justification, non contrôlé directement) | 5k | 10k | half |
|-------------------------------------------------------------------|----|-----|------|
| beginner | 15 | 20 | 25 |
| intermediate | 25 | 30 | 35 |
| advanced | 40 | 45 | 50 |

Un « advanced » déclaré qui court 20 km/sem est refusé sur son niveau : le message propose le niveau en dessous. On ne rétrograde pas automatiquement (décision humaine du coureur).

Messages FR (`message_fr`, `details` en EN) :
- vide : « Indique tes km des 4 dernières semaines : sans ce chiffre, on ne peut pas te proposer un départ sûr. » → `details.reason="recent_weekly_km_missing"`
- trop bas : « Avec environ {ref_km} km/sem en ce moment, un {distance} au niveau {level} n’est pas sûr. Il faut courir au moins {min} km/sem de façon régulière, ou viser une distance plus courte. » → `details={"reason":"recent_volume_below_goal_min","ref_km":…,"required_km":…,"level":…,"distance":…}`

**Cas chiffrés (dont 11 km/sem → semi)** :

| Cas | `recent_weekly_km` | `ref_km` | Résultat attendu |
|-----|--------------------|----------|------------------|
| C1 beginner semi | `[11, 10, 12, 11]` | `min(11, 12)` = 11 | **`VOLUME_TOO_LOW_FOR_GOAL`** (11 < 15). Avant : départ ~31 km/sem. |
| C2 même coureur, 10k | `[11, 10, 12, 11]` | 11 | **`VOLUME_TOO_LOW_FOR_GOAL`** (11 < 13) |
| C3 même coureur, 5k | `[11, 10, 12, 11]` | 11 | PASS : S1 ≤ 12,1 km ; pic = 12,1/0,70 ≈ 17,3 km (≥ 15) |
| C4 beginner semi (example actuel) | `[22, 24, 23, 25]` | `min(23,5, 25)` = 23,5 | PASS : S1 ≤ 25,9 km = min(25,9 ; 0,62×38 = 23,6) → S1 23,6, pic 38 |
| C5 tendance à la baisse (edge injury) | `[30, 28, 25, 22]` | `min(26,5, 25)` = 25 | S1 ≤ 27,5 km (et non 29,2 via la médiane seule) |
| C6 advanced 10k sous-entraîné | `[20, 22, 21, 22]` | 21,5 | **`VOLUME_TOO_LOW_FOR_GOAL`** (21,5 < 29), message propose « intermediate » |
| C7 plancher | `[8, 9, 7, 9]` | 8,5 | **`VOLUME_TOO_LOW_FOR_GOAL`** (< 10), même pour un 5k beginner |
| C8 2 valeurs seulement | `[18, 20]` | `min(19, 20)` = 19 | 10k beginner PASS + warning FR « moins de 4 semaines renseignées » |

Les 9 examples actuels (`examples/*.json`, hors edge) passent tous les seuils ci-dessus.

**Validateur (P0-5, EngineValid)** : `week[1].target_km > week1_cap_km + 0.1` (tolérance d’arrondi) → `VALIDATION_FAILED`, rule_id proposé `R21` / `START_VOLUME_ABOVE_RECENT` (EngineValid fixe l’id final ; R16 et R18 sont déjà pris dans §5). Le validateur doit recevoir `athlete.recent_weekly_km`.

### 3.9 Fourchettes d’allure par zone (P0-1, 2026-10-02)

Pourquoi : une allure unique (« 5:21/km ») est irréaliste au quotidien (terrain, vent, fatigue). On donne une fourchette autour de l’allure de zone Daniels (`pace_zones`, valeur centrale inchangée). La fourchette s’étend **plus du côté lent que du côté rapide** : au doute, plus lent.

| Constante | Côté rapide (`min`) | Côté lent (`max`) | Justification |
|-----------|---------------------|-------------------|---------------|
| `PACE_RANGE_E` | `-3 %` | `+8 %` | Daniels donne l’endurance comme une plage large (~59–74 % VO2max) ; trop lent n’est jamais un risque en E |
| `PACE_RANGE_M` | `-1 %` | `+3 %` | Allure marathon = allure soutenue mais contrôlée |
| `PACE_RANGE_T` | `-1 %` | `+2 %` | Le seuil est précis ; l’erreur classique est d’aller trop vite |
| `PACE_RANGE_I` | `-1 %` | `+2 %` | Idem, effort VO2max court |
| `PACE_RANGE_R` | `-1 %` | `+2 %` | Vitesse ; la forme prime sur le chrono |
| `PACE_RANGE_ROUND_SEC` | `5` | | Affichage lisible (« 6:15–6:40 ») |

Calcul (en secondes/km, `p` = allure de zone) :

```
min = 5 * round(p * (1 - fast_pct) / 5)
max = 5 * round(p * (1 + slow_pct) / 5)
min = min(min, p) ; max = max(max, p)      # p reste toujours dans la fourchette
assert min < max
```

`round` = arrondi au plus proche, `.5` vers le haut (`ROUND_HALF_UP`), pas l’arrondi bancaire Python, pour rester déterministe et lisible. Même règle pour `week1_cap_km` (0,1 km).

Exemples (zones du moteur actuel) :

| VDOT | E | M | T | I | R |
|------|---|---|---|---|---|
| 35 (≈ débutant) | 7:00–7:45 (`p`=7:12) | 5:55–6:10 | 5:35–5:45 | 5:10–5:20 | 4:50–4:55 |
| 51 (ancre 5k 20:00) | 5:10–5:45 (`p`=5:21) | 4:25–4:35 | 4:10–4:15 | 3:50–3:55 | 3:30–3:40 |

Contrôles validateur (P0-6, EngineValid) : `min_sec_per_km < max_sec_per_km` ; l’allure de zone `p` ∈ [min, max] ; fourchette de séance ⊂ fourchette de sa zone ; pas de chevauchement T/I ni I/R (ordre des zones conservé). Fail → `VALIDATION_FAILED`, rule_id proposé `R22` / `PACE_RANGE_INVALID`.

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

Le bas de fourchette handoff reste indicatif. Le refus `VOLUME_TOO_LOW_FOR_GOAL` se décide uniquement avec `RECENT_KM_MIN_FOR_GOAL` (§3.8).

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
| R20 | Volume de départ trop bas pour l’objectif (§3.8 : `ref_km` < `RECENT_KM_MIN_FOR_GOAL` ou < plancher, ou `recent_weekly_km` vide) | `VOLUME_TOO_LOW_FOR_GOAL` |
| R21 | Semaine 1 > `START_VOLUME_MAX_RATIO × ref_km` (+0,1 km d’arrondi) (§3.8) | `VALIDATION_FAILED` |
| R22 | Fourchette d’allure invalide : min ≥ max, zone hors fourchette, ou chevauchement de zones (§3.9) | `VALIDATION_FAILED` |

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
| P08 | Beginner 5k, `recent_weekly_km=[11,10,12,11]`, S1 = 12,1 km | PASS (R21 limite) |
| P09 | Fourchettes VDOT 51 du §3.9 | PASS (R22) |

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
| F15 | `unsafe_start_volume_above_recent.json` | `recent_weekly_km=[11,10,12,11]`, S1 = 31 km | `VALIDATION_FAILED` (R21) |
| F16 | `unsafe_pace_range_inverted.json` | E min 6:40 > max 6:15 | `VALIDATION_FAILED` (R22) |
| F17 | (input, planner) beginner semi, `recent_weekly_km=[11,10,12,11]` | refus avant génération | `VOLUME_TOO_LOW_FOR_GOAL` (R20) |

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
| Volume de départ | median(recent) borné | `min(median, max(2 dernières)) × 1,10`, jamais remonté ; refus sous seuils distance×niveau (2026-10-02, P0-1) |
| Allures | valeur unique par zone | fourchettes asymétriques côté lent, arrondi 5 s (2026-10-02, P0-1) |
