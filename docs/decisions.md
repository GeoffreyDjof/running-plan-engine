# Décisions d’architecture (ADR)

## ADR-001 — Moteur déterministe, pas de calendrier LLM

- **Date** : 2026-09-26
- **Statut** : Accepted
- **Contexte** : Tentation d’utiliser un LLM pour générer semaines / séances ; risque de plans non reproductibles et non sûrs.
- **Décision** : Le calendrier est produit uniquement par le moteur déterministe (templates + planner + paces). Tout LLM (explication / adaptation) doit repasser par le validateur.
- **Conséquences** : Pas de HF/fine-tune v1 pour le calendrier ; `explain` / `adapter` en phases ultérieures ; même input → même output.

## ADR-002 — Contrats Pydantic v2 comme source de vérité

- **Date** : 2026-09-26
- **Statut** : Accepted
- **Contexte** : Besoin d’un contrat JSON stable partagé ArchiPlan / Engine / QA.
- **Décision** : Les modèles Pydantic v2 dans `src/plan_engine/models.py` (forme imbriquée §5 handoff) sont la source de vérité. Le Markdown documente, il ne remplace pas le schéma.
- **Conséquences** : Toute évolution de champ = ADR + mise à jour modèles + exemples + tests ; `extra=forbid` sur les racines Request/Plan.

## ADR-003 — Validateur avant complétude du planner (DoD phase 2)

- **Date** : 2026-09-26
- **Statut** : Accepted
- **Contexte** : Un planner qui produit d’abord des plans agressifs est difficile à sécuriser après coup.
- **Décision** : En phase 2, le validateur et ses fixtures (`valid` + `unsafe_*`) sont livrés **avant** la complétude du planner. Le validateur peut veto un template.
- **Conséquences** : Ordre d’implémentation : modèles → paces → validator → planner ; codes d’erreur validateur listés dans `architecture.md`.

## ADR-004 — Rule ids validateur dans `EngineError.details`, pas dans `ErrorCode`

- **Date** : 2026-09-26
- **Statut** : Accepted
- **Contexte** : DomainCoach : les règles validateur (qualité 2j de suite, long trop long, jump volume, etc.) ne doivent pas polluer l’enum top-level handoff §5.3. Pushback contre l’ajout de `QUALITY_BACK_TO_BACK` etc. comme `ErrorCode`.
- **Décision** : `ErrorCode` reste limité aux 6 codes handoff. Les rule ids validateur sont portés dans `EngineError.details` (ex. `rule_id`, `broken_rules`) avec `code=VALIDATION_FAILED` ou `INJURY_BLOCKS_QUALITY`. Liste de référence dans `models.VALIDATOR_RULE_IDS` / architecture. Promotion d’un rule id en `ErrorCode` = ADR dédiée.
- **Conséquences** : API d’erreur stable pour l’asso ; détail machine-readable pour QA/EngineValid ; pas de breaking change d’enum à chaque nouvelle règle.


## ADR-005 — R01 volume week-to-week vs dernière semaine de charge

- **Date** : 2026-09-26
- **Statut** : Accepted
- **Contexte** : Après deload, le Δ deload→charge (ex. S4→S5 +40 %) est un artefact, pas une hausse de charge. Mesurer R01 vs la semaine précédente brute fausse le veto.
- **Décision** : Pour `VOLUME_JUMP_TOO_HIGH` / R01, le Δ week-to-week se calcule vs la **dernière semaine de charge** (`is_deload=false`), pas vs une deload. Le rebond deload→charge n’est pas un fail R01. Les bornes deload restent R04 (`DELOAD_FRACTION_*` vs pic de charge récent).
- **Conséquences** : DomainCoach met à jour le libellé R01 dans `coaching-rules.md` ; EngineValid aligne le calcul ; pas de nouveau `ErrorCode`.

## ADR-006 — R04 deload vs pic de charge du bloc courant

- **Date** : 2026-09-26
- **Statut** : Accepted
- **Contexte** : Beg 10k : S8 deload ~75 % du pic du *bloc* (ex. 10.9/14.5) mais pas du pic absolu historique du plan (S1). Mesurer vs pic absolu fausse R04.
- **Décision** : « Pic de charge récent » pour R04 = max des `target_km` / volumes des semaines `is_deload=false` **depuis la dernière deload** (bloc courant). Pas le max global du plan.
- **Conséquences** : DomainCoach / EngineValid alignent R04 ; QA doit fournir le contexte `athlete` du `PlanRequest` à `validate_plan` (seuils level-dépendants) — dump nu sans athlete = hors contrat de revue.

## ADR-007 — Contrat P0-2 : PaceRange, as_of_date, warnings structurés

- **Date** : 2026-10-02
- **Statut** : Accepted
- **Contexte** : Le contrat P0 doit préparer trois évolutions sans casser les plans déjà générés : bandes d’allure autour du pace central, date de référence injectable (démo / déterminisme), et warnings machine-lisibles. `ErrorCode` reste limité aux 6 codes handoff (ADR-004). Le planner ne remplit pas encore les bandes (P0-6) ni `as_of_date` / `generated_at` dérivé (P0-7).
- **Décision** :
  - `PaceRange` (`min_sec_per_km`, `max_sec_per_km`, entiers > 0, `min < max` : min = extrémité rapide, max = extrémité lente) et `PaceZoneDetail.range: PaceRange | None = None`. `pace_sec_per_km` reste le pace central ; si `range` est présent, `min <= pace_sec_per_km <= max`. Largeurs DomainCoach (à appliquer par le planner en P0-6, hors de ce contrat) : autour du pace de zone, plus large côté lent, arrondi 5 s — E −3 % / +8 %, M −1 % / +3 %, T/I/R −1 % / +2 % (ex. E à VDOT 35 → 7:00–7:45/km).
  - Date de référence injectable : `options.as_of_date: date | None = None` (pas au top-level `PlanRequest` : c’est une option de calcul, pas un attribut athlète/objectif). Même input + même `as_of_date` → JSON identique. Le plan peut l’echo dans `meta.as_of_date`. `meta.generated_at` est un horodatage **dérivé / déterministe**, pas l’horloge murale (câblage planner en P0-7).
  - `meta.warnings` devient `list[PlanWarning]` (défaut `[]`) avec `code` (id anglais stable, ex. `START_VOLUME_CAPPED`), `message_fr`, `details: dict = {}`. Les warnings ne bloquent pas ; les refus restent `EngineError`.
- **Conséquences** : plans générés actuels (sans `range`, `warnings: []`) restent valides. EngineMoteur câble les bandes (P0-6) et `as_of_date` / `generated_at` (P0-7). EngineValid n’a pas de nouveau `ErrorCode`. Les `list[str]` en warnings sont un breaking change volontaire et petit (aucun exemple commité n’avait de chaînes).
