# Plan de correction P1 — running-plan-engine

Version : 2026-10-02 · Base : `main@ed8a5f2` (P0-11 et P0-12 mergées)
Statut : **proposé** · Hors périmètre : CI (reportée sur demande)

Cinq points à corriger, issus de la revue du 2026-10-02 :

| # | Point | ADR |
|---|-------|-----|
| 0 | Compter échauffement / retour au calme dans `total_km` ; exemples régénérés + test golden | ADR-009 |
| 1 | Jour de course exempté du contrôle des minutes ; footing pré-course seulement un jour disponible | ADR-010 |
| 2 | Rééquilibrer les km rognés par les créneaux ; `PlanWarning` au lieu d'un refus | — |
| 3 | Blessure : **trou fonctionnel** (décision porteur) → plan adapté, plus de refus | ADR-008 |
| 4 | Ancre VDOT corrigée, recalibrage multi-points | ADR-011 |

---

## 1. Mesures de départ (baseline)

Générateur aléatoire de 4 000 `PlanRequest` cohérentes (seed 1, `as_of` 2026-10-02 ;
niveaux, distances, disponibilités 30–150 min, km récents 10–70, 10 % de blessures).

| Indicateur (`main@ed8a5f2`) | Valeur | Avant P0-11 (`38a4c14`) |
|---|---|---|
| Plans produits | 772 (19 %) | 794 |
| `VALIDATION_FAILED` | 1 829 (46 %) | 1 810 |
| … refus impliquant `SESSION_OVER_MAX_MINUTES` | 1 700 | 1 703 |
| … refus impliquant `INSUFFICIENT_EASY_RATIO` | 558 | 555 |
| … refus impliquant `MISSING_TAPER` | 478 | 479 |
| … refus impliquant `R04` (allègement) | **73** | 0 |
| Profils blessés (387) ayant obtenu un plan | **0** (262 `INJURY_BLOCKS_QUALITY`, le reste refusé avant ou crash) | 0 |
| Exceptions non typées (crash) | **5** | 0 |
| Plans acceptés avec une semaine de charge < 60 % de S1 | **97** | 6 |
| Plans acceptés avec une séance < 1,5 km | **65** | 0 |
| Séances programmées sur un jour indisponible / non déclaré | 114 | 113 |

`GOAL_TOO_SOON` (570) et `VOLUME_TOO_LOW_FOR_GOAL` (562) sont des refus légitimes vu le générateur.

Constat demo_1 : S1 annonce 14,6 km mais dure l'équivalent de ~20 km à l'allure E
(échauffement 10 min + retour au calme 5 min non comptés), pour une référence de 13,5 km.

Les 4 fichiers `examples/demo/` produisent des plans corrects sur `main` : **la démo du soir
n'est pas impactée** par la régression P0-11.

---

## 2. Principes transverses

1. **Le validateur ne s'assouplit jamais sans ADR.** C'est le planner qui s'adapte.
2. **Une PR par point**, goldens régénérés dans la même PR (jamais édités à la main), diff des
   goldens relu par DomainCoach.
3. Chaque PR colle dans sa description le **rapport du générateur avant / après**.
4. **ADR avant code** pour tout changement de contrat ou de sémantique (ADR-002).
5. **Rollback** : `git revert -m 1 <merge>` ; moteur sans état, aucune migration de données ;
   goldens dans la même PR, donc un revert restaure un état cohérent.
6. `meta.engine_version` incrémentée à chaque changement de comportement (traçabilité des plans).

---

## 3. Séquencement

| Ordre | PR | Contenu | Dépend de | Taille | Owner |
|---|---|---|---|---|---|
| 1 | PR-0 | Filet de sécurité : goldens + tests de propriétés | — | S | QAPlan |
| 2 | PR-1 | Stabilisation P0-11 (crash, effondrement, R04) | PR-0 | S–M | EngineMoteur |
| 3 | PR-2 | **Point 0** — comptage des km | PR-1, ADR-009 | M | ArchiPlan + EngineMoteur + EngineValid |
| 4 | PR-3 | **Point 1** — jour de course | PR-2, ADR-010 | S–M | EngineMoteur + EngineValid |
| 5 | PR-4 | **Point 2** — rééquilibrage + warnings | PR-2, PR-3 | M | EngineMoteur |
| 6 | PR-5 | **Point 3** — mode blessure | PR-3, PR-4, ADR-008 | M | EngineMoteur + DomainCoach |
| 7 | PR-6 | **Point 4** — VDOT | PR-0, ADR-011 | M | EngineMoteur + DomainCoach |

Pourquoi cet ordre :
- Le point 0 change **tous** les volumes : le faire avant 1/2/3 évite de recalibrer deux fois.
- PR-1 vient avant tout le reste : `main` produit aujourd'hui des plans absurdes acceptés.
- Le point 4 ne touche que les allures : développement **en parallèle** dès PR-0, merge en
  dernier (rebase = régénération des goldens).

---

## 4. Détail par PR

### PR-0 — Filet de sécurité (aucun changement de comportement)

**Changements**
- `scripts/regen_examples.py` : pour chaque entrée `examples/*.json` et `examples/demo/*.json`,
  écrit `<entrée>_plan_generated.json` (plan **ou** `EngineError`, donc demo_4 couvert).
  Date de référence : `options.as_of_date` du fichier, sinon `2026-09-26` (exemples historiques).
- `tests/test_golden.py` : sortie générée == fichier commité ; message d'échec :
  « régénérer via `python scripts/regen_examples.py` et relire le diff ».
- `tests/test_planner_properties.py` : générateur déterministe (seed fixe, N ≈ 1 000, < 3 s).
  Invariants, chacun marqué `xfail(strict=True)` jusqu'à la PR qui le corrige :

| Id | Invariant | Corrigé par |
|---|---|---|
| I1 | `generate_plan` ne lève jamais d'exception | PR-1 |
| I2 | Tout `Plan` renvoyé passe `validate_plan` | déjà vrai |
| I3 | Aucune semaine de charge < 0,9 × S1 sans warning explicatif (seuil à valider) | PR-1 |
| I4 | Aucune séance < 2,0 km (hors course) | PR-1 |
| I5 | Aucune séance sur un jour à 0 min ou non déclaré (hors course) | PR-3 |
| I6 | `total_km` = Σ `distance_km` des blocs (±0,1) ; `total_minutes_est` = Σ `duration_min` (±0,5) | PR-2 |
| I7 | `generate_plan` ne renvoie jamais `INJURY_BLOCKS_QUALITY` | PR-5 |
| I8 | Taux `VALIDATION_FAILED` ≤ seuil (cliquet abaissé à chaque PR) | PR-3, PR-4 |

`strict=True` force à retirer le `xfail` dès que l'invariant passe.

- `scripts/fuzz_report.py` : même générateur, imprime le tableau du §1 (observabilité des PR).

**Acceptation** : pytest vert ; goldens = comportement de `main@ed8a5f2` (les fichiers
`*_plan_generated.json` actuels, périmés depuis P0-6/P0-7, sont remplacés).

---

### PR-1 — Stabilisation P0-11 (hotfix)

**Problèmes (reproduits)**
1. `_split_easy` renvoie une part nulle ou négative quand les planchers dépassent le total
   (`_split_easy(3, 3) == [2.0, 2.0, -1.0]`) → `StructureBlock` négatif → exception Pydantic
   (5 / 4 000). Latent avant #17, atteignable depuis.
2. Effondrement du volume : 97 plans acceptés avec une semaine de charge < 60 % de S1
   (ex. débutant semi : 23,6 → 11,4 → … → 5,3 km ; séances de 0,9 km). Hypothèse à confirmer :
   interaction entre la boucle de plafonnement charge→charge
   (`week_km * cap / actual - 0.1`, 6 itérations) et `_rebalance_easy_volume`.
3. R04 (73 refus, 0 avant #17) : mêmes semaines effondrées, ratios d'allègement aberrants
   (0,51 ; 5,16).
4. `_make_session` déclare `total_minutes_est = max_minutes` alors que les blocs font plus
   (créneau de 12 min → blocs 5 + 5 + 5 = 15 min) : le dépassement est masqué au validateur.

**Changements**
- `_split_easy` : si `total < n × plancher`, réduire le nombre de footings (moins de séances,
  jamais de séances minuscules) ; garantir Σ = total et chaque part ≥ plancher.
- Diagnostiquer 2 et 3 à partir des reproducteurs (ajoutés en tests de non-régression) ; corriger
  la boucle de plafonnement pour qu'elle ne puisse pas descendre sous S1.
- `_make_session` : ne jamais mentir sur la durée ; si la séance ne tient pas, la raccourcir ou
  la supprimer.

**Acceptation** : I1, I3, I4 passent ; 0 `R04` dans le rapport ; goldens démo inchangés.

**Repli** : si la cause racine n'est pas corrigée en ≤ 1 jour, `git revert -m 1 ed8a5f2`
(demo_1 redevient plat — problème connu P0-11), et la redistribution est refaite dans PR-4.

---

### PR-2 — Point 0 : compter les km réellement courus

**Problème** : `total_km` = bloc principal seul ; échauffement 10 min + retour au calme 5 min
comptés en minutes, pas en km. Toutes les règles de volume (R01, R04, R15, R21) calculent sur un
chiffre faux de ~2–2,5 km par séance.

**Décision recommandée (ADR-009)** — modèle hybride :
- **Footing / récupération / sortie longue** : un seul bloc `main` en zone E (un échauffement à
  la même allure que la séance n'a pas de sens).
- **Qualité et course** : échauffement + corps + retour au calme, **chaque bloc avec
  `distance_km`** (échauffement et retour au calme = minutes × 60 / allure E).
- `Session.total_km` = Σ `distance_km` des blocs ; `total_minutes_est` = Σ `duration_min`.
- **Part d'endurance calculée par zone de bloc** (zone E = facile), et plus par type de séance.
  Sans ça, compter l'échauffement d'un tempo en « qualité » ferait monter
  `INSUFFICIENT_EASY_RATIO`. C'est aussi plus fidèle à la polarisation (temps passé par zone).

Alternatives écartées :
- « Compter échauffement + retour au calme partout » : des footings structurés en 3 blocs
  identiques, sans bénéfice.
- « Footings d'un seul bloc uniquement » : les séances de qualité restent sous-comptées.

**Changements**
- Constantes `WARMUP_MIN`, `COOLDOWN_MIN` (aujourd'hui 10 / 5 codés en dur à 2 endroits :
  `_make_session` et `_max_km_for_day` de P0-11).
- Une seule source de vérité coût ↔ distance : `_session_blocks(kind, main_km, paces)` et
  `_main_km_for_minutes(kind, minutes, paces)`, utilisées par `_make_session` **et**
  `_max_km_for_day`.
- Parts de qualité des templates (0,14 / 0,15 / 0,17) : à recalibrer, puisqu'elles incluent
  désormais échauffement et retour au calme.
- Validateur : nouvelle règle `SESSION_TOTALS_INCONSISTENT` (I6) ; part d'endurance par zone
  (repli sur le type de séance si les blocs manquent).
- `engine_version` : 0.1.0 → 0.2.0, version unifiée (pyproject, `__init__`, planner →
  `importlib.metadata`).

**Acceptation** : I6 passe ; demo_1 S1 ≤ 14,85 km **réels** ; goldens régénérés et diff relu.

**Risques** : les seuils numériques de `tests/test_demo_1_plan.py` (`min(loads) >= 13.5`,
sortie longue ≤ 75 min) sont à revoir avec DomainCoach ; les séances paraîtront plus courtes
en minutes pour le même volume annoncé (à expliquer au club).

---

### PR-3 — Point 1 : jour de course et footing pré-course

**Problèmes (reproduits)**
- Course un samedi avec 45 min dispo → refus `SESSION_OVER_MAX_MINUTES`.
- Semi avec 90 min dispo le jour J → refus (course 104,7 min).
- Footing pré-course forcé à J-1 : jour déclaré à 0 min → refus ; jour absent → accepté mais
  programmé sur un jour non déclaré (114 séances dans le générateur).

**Décision recommandée (ADR-010)**
1. Nouvelle valeur `SessionKind.race` pour la course (aujourd'hui `race_pace`, confondue avec les
   séances d'allure spécifique dans R07 / R13 / part d'endurance). C'est aussi un prérequis de
   PR-5 : sans elle, R13 bloquerait la course d'un coureur blessé.
   Alternative : `PlanMeta.race_date` additif et repérage de la course par date — moins explicite.
2. La séance `race` est **exemptée** de `SESSION_OVER_MAX_MINUTES` (date fixée par l'organisateur).
3. Un jour **absent** de `availability` = **indisponible** (clarification du contrat ; le
   validateur refuse alors toute séance hors course sur ce jour — fin du fail-open).

**Changements**
- Footing pré-course : candidats = jours à `max_minutes > 0` dans [J-2, J-1], J-1 en priorité ;
  sinon pas de footing pré-course. Plus jamais de disponibilité synthétique hors course.
- Sans `race_date` : le test final est placé sur le jour de sortie longue de la dernière semaine
  (jour disponible) au lieu d'un dimanche synthétique.
- Validateur : exemption `kind == race` ; séance sur un jour absent → erreur.
- `labels.py` / CLI : libellé FR pour `race`.

**Acceptation** : les 3 cas reproduits produisent un plan ; « vendredi à 0 min » et
« vendredi absent » donnent le même résultat ; I5 passe ; cliquet I8 abaissé.

**Hors périmètre** : `MISSING_TAPER` pour un semi couru du lundi au mercredi (le calendrier
suppose une course le dimanche) → ticket séparé.

---

### PR-4 — Point 2 : rééquilibrer et avertir au lieu de refuser

**Acquis P0-11** : footings et sortie longue redistribués dans les plafonds ; warning
`VOLUME_CAPPED_BY_AVAILABILITY`.

**Reste** : la séance de qualité n'est « jamais touchée » ; avec des créneaux de 30–40 min,
les footings sont rognés, la qualité garde 15–17 % → part d'endurance 74 % → refus
(558 refus dans le générateur).

**Changements**
1. Plafonner la qualité **après** rognage et redistribution :
   `qual_km ≤ (1 − EASY_SHARE_TARGET) / EASY_SHARE_TARGET × easy_km` (part d'endurance par
   zone, cf. PR-2) → warning `QUALITY_REDUCED_FOR_EASY_RATIO`.
2. Si le corps de séance devient inférieur au minimum utile (seuil DomainCoach, ex. 15 min au
   seuil) → remplacée par footing + lignes droites → warning `QUALITY_REPLACED_BY_AVAILABILITY`.
3. Registre `WARNING_CODES` dans `constants.py` ; test : tout code émis ∈ registre.
4. Refus seulement si les contraintes dures restent impossibles après adaptation → erreur
   `INSUFFICIENT_AVAILABILITY` avec message FR explicite, pas `VALIDATION_FAILED`.

**Acceptation** : profils 30 / 40 min en semaine → plan + warnings ; tout plan adapté porte un
warning ; `VALIDATION_FAILED` < 5 % dans le générateur (hors cas `MISSING_TAPER` jour de semaine,
suivis à part).

---

### PR-5 — Point 3 : mode blessure (plan adapté)

**Problème** : le planner ignore `constraints.injuries` ; le validateur refuse donc 100 % des
profils blessés (R13 + `LONG_RUN_OVER_CEILING` à 30 %), même en 5 km débutant.

**Changements** (selon ADR-008, brouillon en annexe)
- Si `injuries` est non vide :
  - toutes les séances de qualité (et par défaut les lignes droites) → footing ;
  - part de sortie longue ≤ `INJURY_LONG_RUN_SHARE_CAP` (0,30), passée à
    `_rebalance_easy_volume` et à la boucle de plafonnement ;
  - séance `race_pace` d'affûtage → footing ; la course (`SessionKind.race`) est maintenue ;
  - warning `INJURY_ADAPTED` : « Blessure déclarée : plan sans séance de qualité, sortie longue
    limitée à 30 %. Fais valider la reprise par un professionnel de santé. »
- Validateur inchangé (R13 et le plafond blessure restent des garde-fous) ; le code
  `INJURY_BLOCKS_QUALITY` reste dans l'enum (ADR-004), il ne doit plus sortir que d'un bug (I7).
- `examples/edge_injury_quality_blocked.json` → renommé `edge_injury_adapted.json`, golden = plan.

**Acceptation** : 9 templates × blessure → plan ; aucune séance de qualité hors course ; sortie
longue ≤ 30 % ; warning présent ; I7 passe.

---

### PR-6 — Point 4 : ancre VDOT et recalibrage

**Problème** : la spec ancre « 5 km en 20:00 → VDOT 51 ». Les tables Daniels donnent
VDOT 50 ↔ 19:57 et VDOT 51 ↔ 19:36, donc 20:00 ≈ **49,8** — exactement la valeur de la régression
brute (49,81). `VDOT_TABLE_SCALE` gonfle le VDOT de 2,4 % : un coureur à 20:00 reçoit les allures
VDOT 51 (seuil 4:11 au lieu d'environ 4:15, marathon 4:26 au lieu d'environ 4:31), contraire au
principe « au doute, plus lent ».

**Options (ADR-011)**
- A. Recaler `ZONE_VO2_FRACTION` sur plusieurs points. Une fraction fixe par zone ne peut pas
  suivre la table de 30 à 70 (le %VO2max d'une zone varie avec le niveau) → erreur croissante
  aux extrêmes.
- **B (recommandée)** : table de référence Daniels VDOT 30–85 (E fourchette, M, T, I, R en s/km)
  en fichier de données `src/plan_engine/data/daniels_vdot_paces.json` + interpolation linéaire
  entre VDOT entiers ; VDOT depuis le temps de course via la formule Daniels brute, sans facteur.
  Exact par rapport à la source, sans coefficient d'ajustement, testable.

**Source** : transcription depuis une source primaire (*Daniels' Running Formula*, édition à
préciser, ou le calculateur officiel VDOT O2). Les sources web secondaires se contredisent
(l'une donne I = 3:20/km à VDOT 50, manifestement faux) → double saisie ou deux sources
indépendantes + tests de monotonie.

**Changements**
- `constants.py` : supprimer `VDOT_TABLE_SCALE` ; `VDOT_ANCHOR_EXPECTED` = 49,8.
- `paces.py` : interpolation dans la table ; fourchettes §3.9 conservées (ou fourchette E de la
  table, à trancher par DomainCoach).
- Docs : `coaching-rules.md` §3.7, `paces-vdot-spec.md` (ancre, tolérance, test d'ancre
  `[50.5, 51.5]` → `[49.7, 49.9]`).
- VDOT par défaut par niveau (35 / 42 / 50) inchangés : ce sont des valeurs de VDOT, pas des temps.

**Tests** : VDOT(5 km, 20:00) ∈ [49,7 ; 49,9] ; aller-retour temps de course 5 / 10 km / semi à
VDOT 30, 40, 50, 60, 70 (±0,3) ; allures = table aux VDOT entiers ; monotonie ; ordre E > M > T > I ≥ R.

**Impact** : toutes les allures ~1,5–2,5 % plus lentes pour un même benchmark, `meta.vdot`
−2,4 % ; tous les goldens changent ; à annoncer au club.

---

## 5. Décisions à valider (DomainCoach / porteur)

| # | PR | Question | Recommandation |
|---|---|---|---|
| D1 | PR-2 | Part d'endurance par zone de bloc ou par type de séance ? | Par zone |
| D2 | PR-2 | Parts de qualité des templates : corps de séance seul ou séance entière ? | Séance entière, recalibrées |
| D3 | PR-1 | Seuil I3 (semaine de charge vs S1) | 0,9 × S1 sauf warning |
| D4 | PR-3 | `SessionKind.race` ou `PlanMeta.race_date` ? | `SessionKind.race` |
| D5 | PR-3 | Sans `race_date` : garder un test final (semi en solo ?) ou une sortie longue ? | À trancher |
| D6 | PR-4 | Durée minimale utile d'une séance de qualité avant remplacement | 15 min au seuil |
| D7 | PR-5 | Lignes droites autorisées en mode blessure ? Progression du volume réduite ? Course maintenue ? | Non / non en v1 / oui + warning |
| D8 | PR-6 | Source de la table et qui la transcrit | Livre, édition à préciser |

---

## 6. Hors périmètre (tickets à ouvrir)

- CI (ruff, mypy, pytest) — reportée sur demande.
- `MISSING_TAPER` pour une course du lundi au mercredi (calendrier calé sur le dimanche).
- `paces_confidence` ignore la date du benchmark (`paces.paces_confidence()` non utilisée).
- Valeurs par défaut fail-open du validateur (niveau → `intermediate`, distance → `10k`).
- Taxonomie des rule ids (ADR-004) et messages FR/EN mélangés dans `message_fr`.
- Course lointaine : démarrage des mois plus tard sans warning.
- Contenu de la semaine de course (footing pré-course + course uniquement).
- Contrat blessure : `injuries: list[str]` sans statut ni gravité (v1 : toute entrée = active).

---

## Annexe — ADR-008 (brouillon) : blessure déclarée → plan adapté

- **Date** : 2026-10-02
- **Statut** : Proposed
- **Contexte** : `constraints.injuries` non vide ⇒ le planner programme quand même de la qualité
  et une sortie longue > 30 % ; le validateur refuse (R13, `LONG_RUN_OVER_CEILING`). Résultat :
  aucun coureur blessé n'obtient de plan, et le message « reste en endurance facile » n'est suivi
  d'aucune proposition. Le porteur qualifie ce refus de trou fonctionnel.
- **Décision** : en présence d'une blessure déclarée, le moteur produit un plan **adapté** :
  aucune séance de qualité (QUALITY_HARD, QUALITY_TEMPO, lignes droites), sortie longue
  ≤ `INJURY_LONG_RUN_SHARE_CAP`, course maintenue, warning `INJURY_ADAPTED` invitant à faire
  valider la reprise par un professionnel de santé. Toute entrée de `injuries` est considérée
  active (prudence, faute de statut dans le contrat).
- **Conséquences** : R13 et le plafond blessure restent des garde-fous du validateur ;
  `INJURY_BLOCKS_QUALITY` reste dans `ErrorCode` (ADR-004) mais ne doit plus être renvoyé par
  `generate_plan` (test de propriété I7). Un statut / une gravité de blessure dans le contrat
  fera l'objet d'une ADR ultérieure.
