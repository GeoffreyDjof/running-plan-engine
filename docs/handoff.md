# HANDOFF — Application plans d'entraînement running (asso)

Document destiné à une équipe d'agents Grok.
Objectif : amorcer le projet, constituer l'équipe, livrer d'abord le **moteur**, puis l'application complète.

Langue de travail : **français**.
Code, identifiants, JSON, tests : **anglais**.
Commentaires métier dans le code : français OK si utile, sinon anglais.

Version : 2026-09-26 (texte intégral Geoffrey).

---

## 0. Comment utiliser ce document

1. Lire intégralement avant de coder.
2. Constituer l'équipe (section 3) et assigner un owner par livrable.
3. Ne pas sauter la phase 0 (cadrage + contrat d'interface).
4. Ne pas commencer par le design UI, le fine-tune LLM, ni Hugging Face.
5. Chaque phase a une **Definition of Done**. Rien ne passe à la phase suivante sans DoD verte.
6. Toute décision qui change le contrat JSON ou une règle de sécurité doit être écrite dans `docs/decisions.md` (ADR courte).

Le porteur humain du projet est novice en datasets / Hugging Face. L'équipe doit produire du code lisible, testé, documenté, et expliquer les choix métier.

---

## 1. Vision produit (une phrase)

Permettre à une association de running de **générer, valider et adapter** des plans d'entraînement personnalisés, sûrs et structurés, à partir du profil, de l'objectif et des contraintes d'un coureur — sans laisser un LLM inventer le calendrier.

### 1.1 Périmètre v1 (moteur)

Inclus :
- génération d'un plan semaine par semaine, séance par séance
- calibration d'allures (VDOT / équivalent)
- templates 5 km, 10 km, semi, marathon
- niveaux beginner / intermediate / advanced
- 3 à 6 séances / semaine
- validateur de sécurité (charge, intensité, repos, blessure)
- API / fonction Python pure : `generate_plan(input) -> Plan`
- tests unitaires + cas métier

Exclus v1 :
- UI, design, auth, paiement
- import Strava / Garmin
- génération libre par LLM du calendrier
- nutrition, musculation avancée, trail technique
- multi-athlète coaching dashboard (v2)

### 1.2 Périmètre application complète (après le moteur)

Ordre imposé :
1. Moteur + tests + CLI
2. API HTTP
3. App web minimale (formulaire profil → plan lisible)
4. Compte asso / coureur
5. Export ICS + PDF
6. Adaptation « séance manquée »
7. Import Strava/Garmin (option)
8. LLM **d'explication et d'adaptation contrainte**, jamais de génération brute du plan

### 1.3 Utilisateurs

- Coureur adhérent : reçoit un plan
- Coach / référent asso : valide les règles, peut override
- Admin asso : paramètre les templates et garde-fous

---

## 2. Principes non négociables

1. **Le plan est déterministe.** Même input → même output (hors seed d'adaptation explicite).
2. **Le LLM n'écrit pas le calendrier.** Il reformule, explique, propose une adaptation qui repasse dans le validateur.
3. **Sécurité > personnalisation.** En cas de doute, plan plus conservateur.
4. **Sortie JSON schema-validée.** Pas de Markdown comme source de vérité.
5. **Pas de Hugging Face en v1.** Les datasets HF (Endomondo, CoachTwin, SmartFit, etc.) ne sont pas des plans. Interdit de fine-tuner un modèle dessus pour générer le calendrier.
6. **Progression bornée.** On ne double jamais le volume d'un coup. Semaine de décharge périodique. Taper avant course.
7. **Allures calibrées** à partir d'une perf récente (ou estimation conservative si absente).
8. **Blessure / douleur** : pas de fractionné VO2 / reps si contrainte récente non levée.
9. **Code testé d'abord.** Chaque règle métier = au moins un test.
10. **L'asso doit pouvoir lire le plan.** Séances nommées clairement, structure type `WU + corps + CD`.

---

## 3. Équipe d'agents (déjà constituée)

| Rôle | Agent | Livrables |
|---|---|---|
| Orchestrateur / PM | PlanOrch | roadmap, DoD, recap humain |
| Domain Coach | DomainCoach | `docs/coaching-rules.md`, cas métier |
| Architecte | ArchiPlan | `docs/architecture.md`, schémas Pydantic |
| Engineer moteur | EngineMoteur | package `plan_engine` (paces, templates, planner) |
| Engineer validateur | EngineValid | `validator.py` + tests |
| QA | QAPlan | matrice, couverture métier |

API / Frontend / Designer / Integrations : plus tard (phases 5+).

---

## 4. Stack technique imposée (v1)

- Python 3.12+
- Pydantic v2 (contrats)
- pytest
- ruff + mypy (strict raisonnable)
- Git repo unique
- Pas de framework web en phase 0–1
- Dépendances minimales : `pydantic`, `pytest`. Ajouter `fastapi` / `uvicorn` seulement en phase 2 (API = phase 5 handoff).

Structure cible :

```text
running-plan-engine/
  README.md
  pyproject.toml
  docs/
    architecture.md
    coaching-rules.md
    decisions.md
    handoff.md
  src/plan_engine/
    __init__.py
    models.py
    paces.py
    templates/
    planner.py
    validator.py
    adapter.py
    explain.py
  tests/
    test_paces.py
    test_planner.py
    test_validator.py
    fixtures/
  examples/
    beginner_10k.json
    intermediate_half.json
  scripts/
    generate_cli.py
```

---

## 5. Contrat d'interface (cœur du projet)

### 5.1 Input

```json
{
  "athlete": {
    "id": "optional-string",
    "age": 34,
    "sex": "female",
    "experience_years": 2,
    "level": "intermediate",
    "recent_weekly_km": [28, 32, 30, 24],
    "longest_run_km_last_4w": 16,
    "availability": [
      {"weekday": "tue", "max_minutes": 60},
      {"weekday": "thu", "max_minutes": 70},
      {"weekday": "sat", "max_minutes": 120},
      {"weekday": "sun", "max_minutes": 50}
    ],
    "constraints": {
      "injuries": [],
      "no_track": false,
      "prefers_time_based": false
    }
  },
  "benchmark": {
    "distance_km": 10,
    "time_sec": 2940,
    "date": "2026-08-15",
    "is_estimate": false
  },
  "goal": {
    "distance_km": 21.0975,
    "race_date": "2026-12-06",
    "target_time_sec": null
  },
  "options": {
    "sessions_per_week": 4,
    "include_strength": true,
    "units": "metric",
    "language": "fr"
  }
}
```

Champs critiques :
- `level` : `beginner` | `intermediate` | `advanced`
- `recent_weekly_km` : 4 semaines, plus récente en dernier
- si pas de `benchmark` : estimer un VDOT **conservateur** à partir du niveau + volume, et flagger `paces_confidence: low`
- `sessions_per_week` doit être compatible avec `availability` (sinon erreur métier, pas de plan silencieux)

### 5.2 Output

```json
{
  "meta": {
    "engine_version": "0.1.0",
    "generated_at": "2026-09-26T08:00:00Z",
    "method": "vdot_templates_v1",
    "vdot": 42.3,
    "paces_confidence": "high",
    "start_date": "2026-09-28",
    "weeks": 12,
    "warnings": []
  },
  "pace_zones": {
    "E": {"pace_sec_per_km": 340, "label": "Endurance / Easy"},
    "M": {"pace_sec_per_km": 300, "label": "Marathon"},
    "T": {"pace_sec_per_km": 282, "label": "Seuil / Threshold"},
    "I": {"pace_sec_per_km": 260, "label": "Intervalle VO2"},
    "R": {"pace_sec_per_km": 242, "label": "Répétitions"}
  },
  "plan": [
    {
      "week_index": 1,
      "phase": "base",
      "target_km": 32,
      "is_deload": false,
      "sessions": [
        {
          "id": "w1-tue",
          "weekday": "tue",
          "date": "2026-09-29",
          "kind": "easy",
          "title": "Footing endurance",
          "structure": [
            {"block": "warmup", "duration_min": 10, "zone": "E"},
            {"block": "main", "distance_km": 7, "zone": "E"},
            {"block": "cooldown", "duration_min": 5, "zone": "E"}
          ],
          "total_km": 9.0,
          "total_minutes_est": 55,
          "load": "easy",
          "notes_fr": "Allure conversationnelle. Si essoufflé, ralentir."
        }
      ]
    }
  ]
}
```

`kind` autorisés v1 :
`rest` | `easy` | `long` | `strides` | `tempo` | `cruise_intervals` | `intervals` | `reps` | `race_pace` | `recovery` | `strength` | `cross`

`phase` : `base` | `development` | `specific` | `taper` | `race`

### 5.3 Erreurs métier

Ne jamais renvoyer un plan invalide. Renvoyer une erreur typée :

- `INSUFFICIENT_AVAILABILITY`
- `GOAL_TOO_SOON`
- `VOLUME_TOO_LOW_FOR_GOAL`
- `BENCHMARK_IMPLAUSIBLE`
- `INJURY_BLOCKS_QUALITY`
- `VALIDATION_FAILED` (détail des règles cassées)

---

## 6. Règles métier v1 (à implémenter telles quelles, puis affiner)

Le Domain Coach peut ajuster les constantes, pas supprimer les catégories.

### 6.1 Calibration

- Si benchmark < 6 semaines et distance ∈ {5, 10, 21.1, 42.2} : VDOT standard Daniels / Gilbert.
- Si benchmark plus vieux : baisser la confiance, éventuellement −1 à −3 VDOT.
- Si temps cible plus ambitieux que le VDOT actuel de > ~8–10 % : warning `GOAL_AMBITIOUS`, ne pas accélérer les allures au-delà du VDOT actuel. Le plan vise la progression, pas le fantasme.
- Allures stockées en secondes / km.

### 6.2 Volume de départ

```text
start_volume = median(recent_weekly_km)
start_volume = min(start_volume, longest_run_km_last_4w * facteur_niveau)
```

Facteurs initiaux (à confirmer par tests métier) :
- beginner : long run ≤ 35 % du volume hebdo, volume max v1 selon distance
- intermediate : long run ≤ 35–40 %
- advanced : long run ≤ 40 %

Plafonds de volume cible en pic (garde-fous v1, pas des idéaux élite) :

| Objectif | Beginner pic | Intermediate pic | Advanced pic |
|---|---|---|---|
| 5 km | 25–35 km | 35–50 km | 50–70 km |
| 10 km | 30–40 km | 40–60 km | 55–80 km |
| Semi | 35–45 km | 45–65 km | 60–90 km |
| Marathon | 40–50 km | 55–75 km | 70–110 km |

Si le volume actuel est très bas pour l'objectif (ex. 15 km/sem. pour un marathon dans 12 semaines) : soit allonger (si date le permet), soit `VOLUME_TOO_LOW_FOR_GOAL` avec alternative « plan finisher conservateur ».

### 6.3 Progression

- +5 à +10 % de volume entre semaines de charge
- 1 semaine deload toutes les 3 ou 4 semaines (volume ~70–80 %)
- jamais 2 semaines consécutives d'augmentation si la précédente dépassait +10 %
- taper :
  - 5/10 km : 7–10 jours
  - semi : 10–14 jours
  - marathon : 14–21 jours
- dernière grosse qualité : ≥ 7–10 jours avant la course selon distance

### 6.4 Intensité (polarisé souple)

Sur une semaine de charge hors taper :
- ≥ 75–80 % du temps/km en Easy / Recovery / Long easy
- au plus **une** séance « très qualité » (intervals ou reps)
- tempo / seuil : 0 ou 1
- pas de qualité dure deux jours calendaires de suite
- lendemain de long run : easy ou rest
- beginner : pas de reps courtes agressives en v1 ; max 1 qualité / semaine au début

### 6.5 Structure d'une semaine type (4 séances)

Exemple intermédiaire semi :
- Mar : qualité (I ou T selon phase)
- Jeu : easy + strides éventuels
- Sam : long
- Dim : recovery easy ou rest
- Strength : jours easy, jamais la veille d'une grosse qualité si fatigue déclarée

Adapter aux jours `availability`. Le long run va sur le jour avec `max_minutes` le plus élevé.

### 6.6 Durée vs disponibilité

Chaque séance `total_minutes_est` ≤ `max_minutes` du jour.
Sinon : raccourcir le easy / couper un intervalle / déplacer. Si impossible : erreur.

### 6.7 Blessures

Si `injuries` contient une contrainte récente (genou, tibia, tendon, periostite, etc.) :
- interdire intervals / reps
- plafonner le long run
- privilégier time-based easy
- warning obligatoire dans `meta.warnings`

Ne pas inventer de diagnostic. Le moteur est conservateur.

### 6.8 Durée du plan

```text
weeks = clamp(days_to_race / 7, min_weeks[distance], max_weeks[distance])
```

Repères v1 :
- 5 km : 6–10 semaines
- 10 km : 8–12
- semi : 10–16
- marathon : 14–20

Si `GOAL_TOO_SOON` : proposer un plan « arriver en forme raisonnable / finisher » plutôt que le temps cible.

---

## 7. Templates — logique, pas 200 fichiers magiques

Ne pas hardcoder 16 semaines × 4 distances à la main dans 64 fichiers copiés.

Approche :
1. Définir des **blocs de phase** (base, development, specific, taper).
2. Chaque phase a un motif de semaine par `sessions_per_week`.
3. Le planner scale le volume et choisit le type de qualité selon la phase.
4. Les distances de fractionné sont dérivées des allures et du budget minutes.

Exemple de motif 4 séances, phase development :
`quality_I | easy_strides | long | recovery`

Phase specific marathon :
`quality_T_or_MP | easy | long_with_MP_finish | recovery`

---

## 8. Phases d'exécution

### Phase 0 — Cadrage
Livrables : repo + handoff, architecture.md, modèles Pydantic, coaching-rules.md constantes.
DoD : l'humain peut lire les 3 docs et dire oui / ajuster.

### Phase 1 — Paces
paces.py VDOT + zones E M T I R. Tests : 20:00 au 5 km → VDOT ~51 ; temps absurde → BENCHMARK_IMPLAUSIBLE.

### Phase 2 — Validateur avant le planner
Fixtures manuelles. Règles : qualité 2j suite ; long > % ; volume >+12% ; >max_minutes ; beginner+reps ; injury+intervals ; easy insuffisant ; taper absent.

### Phase 3 — Planner
Ordre : 10k int 4s → beg/adv 10k → 5k → semi → marathon conservateur.

### Phase 4 — Qualité moteur
Matrice QA, snapshots, README, engine_version.

### Phase 5+ — API, app, adapter, LLM explication seulement

---

## 9–11. Anti-patterns

Interdit : HF fine-tune calendrier, plan Markdown parsé, UI avant validateur, microservices, coller Pfitz tel quel, LLM qui produit les km.

---

## 12. Defaults phase 0

1. Distances : 5 / 10 / semi / marathon
2. Unités : km / min/km
3. Force : 1 séance optionnelle courte
4. Trail / D+ : non v1
5. Constantes volume : conservatrices de ce doc (sauf override humain)
6. Stack app plus tard : FastAPI + front simple

---

## 13. Message d'ouverture (déjà envoyé à Geoffrey via dr eggbot / PlanOrch)

Équipe constituée. Contrat JSON + VDOT + validateur, pas l'UI.
Prochain livrable : coaching-rules.md + 3 exemples input + 1 plan 10 km intermediate validé.
Question plafonds volume asso vs tableau 6.2.
