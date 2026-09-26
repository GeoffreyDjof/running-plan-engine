# Matrice QA métier — DRAFT

> **Statut : draft — exécution phase 4 démarrée (ACC-01 VERT)**  
> Date : 2026-09-26 (Europe/Paris)  
> Source : `docs/handoff.md` (bootstrap phase 0–1) + profil QAPlan / Archi / DomainCoach / EngineValid  
> Langue : rapports humains FR ; ids de cas / fixtures / codes d’erreur EN  
> Distances v1 uniquement : `5k` | `10k` | `half` (semi) | `marathon` — pas de trail / ultra  
> Rapport phase 4 : [`docs/qa-phase4-report-10k-int.md`](qa-phase4-report-10k-int.md)

---

## 0. Prérequis d’exécution (bloquants)

| Composant | Attendu | État box (2026-09-26 PM) |
|-----------|---------|------------------------|
| `src/plan_engine/paces.py` | VDOT + `pace_zones` (E/M/T/I/R) | **PRÉSENT** |
| `src/plan_engine/validator.py` | Contraintes sécurité + codes typés | **PRÉSENT** |
| `src/plan_engine/planner.py` | `generate_plan(PlanRequest) -> Plan` | **PRÉSENT** (template `intermediate_10k_4x` seul) |
| Fixtures `tests/fixtures/` | `valid_plan.json`, `unsafe_*.json` | **PRÉSENT** (1 valid + 15 unsafe) |
| pytest | Snapshot JSON stables + couverture métier | **38 passed** (phase 3 DoD) |

**Règle livrable QAPlan** : après planner, passer chaque case rouge/vert. Phase 4 : **HP-10k-int-s4-inj0 / ACC-01 = VERT** ; reste de la grille encore bloqué (pas d’autres templates).

---

## 1. Axes de couverture

| Axe | Valeurs v1 |
|-----|------------|
| `distance` | `5k`, `10k`, `half`, `marathon` |
| `level` | `beginner`, `intermediate`, `advanced` |
| `sessions_per_week` | `3`, `4`, `5`, `6` (typiques v1 ; handoff bootstrap ne fixe pas une enum stricte) |
| `injury` | `false` (non), `true` (oui — récente : interdit intervals/reps, plafonner long, easy time-based, warning) |

**Espace combinatoire brut** : 4 × 3 × 4 × 2 = **96** cellules.  
Toutes ne sont pas des happy paths : certaines doivent **échouer clairement** (volume / dispo / délai / blessure). La grille §2 sélectionne les cases prioritaires ; la grille §3 couvre les erreurs typées.

### Plafonds pic km/sem (handoff — garde-fous)

| Objectif | Beg | Int | Adv |
|----------|-----|-----|-----|
| 5k | 25–35 | 35–50 | 50–70 |
| 10k | 30–40 | 40–60 | 55–80 |
| Semi | 35–45 | 45–65 | 60–90 |
| Marathon | 40–50 | 55–75 | 70–110 |

---

## 2. Happy paths prioritaires (génération + validation)

Convention id : `HP-<distance>-<level>-s<N>-inj<0|1>`  
Attendu commun happy path :

1. Plan déterministe, JSON schema-validé (Pydantic).
2. Toutes les allures **uniquement** via `pace_zones` (secondes/km) — jamais inventées ailleurs.
3. Volume / polarisation / taper / long-run respectent `coaching-rules` (quand disponible).
4. **100 % des happy paths générés passent le validateur.**
5. Messages / `notes_fr` clairs si warnings (injury).

| # | id | distance | level | sess/sem | injury | Semaines cibles | Attendu |
|---|----|----------|-------|----------|--------|-----------------|---------|
| 1 | HP-10k-int-s4-inj0 | 10k | intermediate | 4 | non | **11** (cible ~12) | **VERT** (2026-09-26) — ACC-01 ; fixture → 11 sem ; validate OK ; pace_zones only ; artifact stable — voir `qa-phase4-report-10k-int.md` |
| 2 | HP-10k-int-s4-inj0-10w | 10k | intermediate | 4 | non | 10 | Variante durée template #1 (10–12 sem) |
| 3 | HP-10k-beg-s3-inj0 | 10k | beginner | 3 | non | 12 | Bas volume, polarisé easy |
| 4 | HP-10k-beg-s4-inj0 | 10k | beginner | 4 | non | 12 | Template ordre #2 |
| 5 | HP-10k-adv-s5-inj0 | 10k | advanced | 5 | non | 12 | Volume dans plafond int/adv 10k |
| 6 | HP-10k-adv-s6-inj0 | 10k | advanced | 6 | non | 10–12 | Haut volume encore ≤ plafond |
| 7 | HP-5k-beg-s3-inj0 | 5k | beginner | 3 | non | 8–10 | Première distance courte |
| 8 | HP-5k-int-s4-inj0 | 5k | intermediate | 4 | non | 8–10 | Ordre templates #3 |
| 9 | HP-5k-adv-s5-inj0 | 5k | advanced | 5 | non | 8–10 | Qualité bornée (≤1 très-qualité) |
| 10 | HP-half-beg-s3-inj0 | half | beginner | 3 | non | 12–14 | Conservateur |
| 11 | HP-half-int-s4-inj0 | half | intermediate | 4 | non | 12–14 | Ordre templates #4 |
| 12 | HP-half-adv-s5-inj0 | half | advanced | 5 | non | 12–16 | Taper 10–14 j |
| 13 | HP-mar-beg-s3-inj0 | marathon | beginner | 3 | non | 16–20 | **§10** : bas volume → **finisher** (jamais pic 70 km sem4) |
| 14 | HP-mar-beg-s4-inj0 | marathon | beginner | 4 | non | 16–20 | Finisher ; pic ≤ plafond beg 40–50 |
| 15 | HP-mar-int-s4-inj0 | marathon | intermediate | 4 | non | 16–20 | Conservateur asso |
| 16 | HP-mar-int-s5-inj0 | marathon | intermediate | 5 | non | 16–20 | Ordre templates #5 |
| 17 | HP-mar-adv-s5-inj0 | marathon | advanced | 5 | non | 16–20 | Pic ≤ 70–110, progression bornée |
| 18 | HP-10k-int-s4-inj1 | 10k | intermediate | 4 | **oui** | 12 | Happy path blessé : pas intervals/reps ; warning ; easy time-based |
| 19 | HP-5k-beg-s3-inj1 | 5k | beginner | 3 | **oui** | 8–10 | Plan sûr sans qualité dure |
| 20 | HP-half-int-s4-inj1 | half | intermediate | 4 | **oui** | 12–14 | Long plafonné + recovery |
| 21 | HP-mar-beg-s3-inj1 | marathon | beginner | 3 | **oui** | 16–20 | Finisher encore plus conservateur |
| 22 | HP-10k-int-s5-inj0 | 10k | intermediate | 5 | non | 12 | Dispo compatible 5 séances |
| 23 | HP-5k-int-s3-inj0 | 5k | intermediate | 3 | non | 8–10 | Bas volume intermediate OK |
| 24 | HP-half-beg-s4-inj0 | half | beginner | 4 | non | 12–14 | Beg + 4 séances semi |

**Sous-total happy paths prioritaires : 24**  
(Extension phase 4 : remplir le reste du cube 96 en ne gardant que les cellules « availability + volume de départ plausibles » — documenter les exclus comme ERR, pas comme skips silencieux.)

### Assertions transverses happy path

| Assertion | Réf. |
|-----------|------|
| Allures uniquement depuis `pace_zones` | QAPlan §10 / EngineMoteur |
| ≥75–80 % easy hors taper | handoff polarisé |
| ≤1 très-qualité + ≤1 tempo / sem ; pas qualité dure 2 j de suite | handoff + EngineValid |
| Long ≤35–40 % volume selon level ; lendemain long = easy/rest | handoff |
| +5–10 % charge ; deload 70–80 % toutes 3–4 sem | handoff |
| Taper : 5/10k 7–10 j ; semi 10–14 ; marathon 14–21 | handoff |
| Snapshot JSON stable (`engine_version` + input → même output) | QAPlan |

---

## 3. Cas d’erreur typées (Archi)

Codes attendus (anglais) ; **message utilisateur en français clair** (jamais d’erreur « impossible » opaque).

| # | id | Code | Scénario (input) | Attendu |
|---|----|------|------------------|---------|
| E1 | ERR-INSUFFICIENT_AVAILABILITY-01 | `INSUFFICIENT_AVAILABILITY` | `sessions_per_week=5` mais jours dispo / `max_minutes` insuffisants pour tenir volume min distance×level | Erreur métier, **pas** de plan silencieux sous-dimensionné |
| E2 | ERR-INSUFFICIENT_AVAILABILITY-02 | `INSUFFICIENT_AVAILABILITY` | Marathon intermediate, 3 séances, créneaux trop courts pour long run | Idem |
| E3 | ERR-GOAL_TOO_SOON-01 | `GOAL_TOO_SOON` | Marathon beginner, course dans &lt; ~12–14 sem (seuil à confirmer DomainCoach) | Refus clair FR |
| E4 | ERR-GOAL_TOO_SOON-02 | `GOAL_TOO_SOON` | 10k beginner, délai &lt; fenêtre min template | Refus clair FR |
| E5 | ERR-VOLUME_TOO_LOW-01 | `VOLUME_TOO_LOW_FOR_GOAL` | Marathon + `recent_weekly_km` très bas + level advanced exigé | Erreur ou orientation finisher — **jamais** montée agressive type 70 km sem4 pour beg |
| E6 | ERR-VOLUME_TOO_LOW-02 | `VOLUME_TOO_LOW_FOR_GOAL` | Semi advanced avec volume départ &lt;&lt; plafond / start median | Refus ou downgrade explicite |
| E7 | ERR-BENCHMARK_IMPLAUSIBLE-01 | `BENCHMARK_IMPLAUSIBLE` | 5k en 8:00 (absurde) | Phase 1 paces — DoD |
| E8 | ERR-BENCHMARK_IMPLAUSIBLE-02 | `BENCHMARK_IMPLAUSIBLE` | 5k en 60:00 pour advanced « élite » incohérent / outlier documenté | Selon règles DomainCoach |
| E9 | ERR-INJURY_BLOCKS_QUALITY-01 | `INJURY_BLOCKS_QUALITY` | `injury=true` + demande explicite intervals/reps / plan qui en injecte | Échec validation / planification qualité |
| E10 | ERR-INJURY_BLOCKS_QUALITY-02 | `INJURY_BLOCKS_QUALITY` | Fixture `unsafe_injury_intervals.json` | EngineValid DoD |
| E11 | ERR-VALIDATION_FAILED-01 | `VALIDATION_FAILED` | Qualité dure 2 jours de suite (`unsafe_back_to_back_quality`) | Code + détail |
| E12 | ERR-VALIDATION_FAILED-02 | `VALIDATION_FAILED` | Long run &gt; plafond % level | Code + détail |
| E13 | ERR-VALIDATION_FAILED-03 | `VALIDATION_FAILED` | Hausse week-to-week &gt; +12 % hors cas documenté | Code + détail |
| E14 | ERR-VALIDATION_FAILED-04 | `VALIDATION_FAILED` | Séance &gt; `max_minutes` | Code + détail |
| E15 | ERR-VALIDATION_FAILED-05 | `VALIDATION_FAILED` | Beginner + reps agressives | Code + détail |
| E16 | ERR-VALIDATION_FAILED-06 | `VALIDATION_FAILED` | Semaine charge &lt; 75–80 % easy | Code + détail |
| E17 | ERR-VALIDATION_FAILED-07 | `VALIDATION_FAILED` | Course dans le plan **sans** taper | Code + détail |
| E18 | ERR-VALIDATION_FAILED-08 | `VALIDATION_FAILED` | Allure hors `pace_zones` / hardcodée | Code + détail |

**Sous-total cas erreur typées : 18** (+ fixtures `unsafe_*` à aligner 1:1 avec EngineValid).

---

## 4. Critères d’acceptation globaux (profil QAPlan / handoff §10)

> Le handoff box est un **extrait bootstrap** (pas de sections numérotées §4 / §6.2 / §10 complètes). Critères ci-dessous = contrat QAPlan confirmé PlanOrch + mentions handoff.

| ID | Critère | Case(s) |
|----|---------|---------|
| ACC-01 | Plan **10k intermediate 4 séances / ~12 semaines** généré + validé | HP-10k-int-s4-inj0 — **VERT** (11 sem sur fixture actuelle) |
| ACC-02 | **Beginner bas volume marathon** → plan **finisher** **ou** erreur claire ; **jamais 70 km en semaine 4** | HP-mar-beg-s3-inj0, HP-mar-beg-s4-inj0, E5 |
| ACC-03 | Allures **seulement** via `pace_zones` | Assertions transverses + E18 |
| ACC-04 | Erreurs impossibles / refus métier en **français clair** | Tous ERR-* |
| ACC-05 | 100 % happy paths générés passent le validateur | §2 après planner |
| ACC-06 | Paces DoD : 5k 20:00 → VDOT ≈ 51 ; absurd → `BENCHMARK_IMPLAUSIBLE` | E7 + test unit paces |
| ACC-07 | Validateur avant planner : `valid_plan.json` OK ; chaque `unsafe_*.json` échoue au bon code | E9–E18 |

---

## 5. Snapshots & rapport

Quand l’exécution sera débloquée :

1. `pytest` + snapshots JSON sous `tests/snapshots/` (clés stables, pas de timestamps flottants).
2. Rapport couverture métier FR : tableau case → vert/rouge + code d’erreur observé.
3. Ne **pas** merger en contournant DomainCoach / EngineValid ; ne **pas** inventer de distances hors v1.

### Compteurs draft

| Catégorie | Nombre |
|-----------|--------|
| Happy paths prioritaires | **24** |
| Cas erreur typées | **18** |
| Critères acceptation tracés | **7** |
| Cellules cube théorique (à échantillonner plus tard) | 96 |

---

## 6. Prochaines actions

1. ~~paces + validator + planner intermediate_10k_4x~~ **fait** (phase 1–3).  
2. QAPlan : **ACC-01 VERT** — rapport `docs/qa-phase4-report-10k-int.md`.  
3. EngineMoteur : autres templates (beg/adv, 5k/half/mar, inj) pour débloquer HP #2–24.  
4. QAPlan : exécuter le reste de la matrice → promouvoir draft → `docs/qa-matrix.md` quand ≥3 HP verts.

