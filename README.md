# running-plan-engine

Moteur **déterministe** de plans d’entraînement running (5 km / 10 km / semi / marathon).
Entrée–sortie JSON validée (Pydantic v2). Pas de calendrier généré par LLM.

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Tests

```bash
pytest -q
```

## Démo en 1 commande

Quatre profils de répétition QA, datés du **2026-10-02** (`options.as_of_date` déjà dans chaque fichier — pas besoin de `--as-of`) :

```bash
python -m plan_engine.cli examples/demo/demo_1_beginner_5k.json
# → plan 5 km débutant (10 semaines, départ 2026-10-05)

python -m plan_engine.cli examples/demo/demo_2_intermediate_10k.json
# → plan 10 km intermédiaire (11 semaines, départ 2026-10-05)

python -m plan_engine.cli examples/demo/demo_3_advanced_half.json
# → plan semi confirmé (12 semaines, départ 2026-10-05)

python -m plan_engine.cli examples/demo/demo_4_undertrained_beginner_half.json
# → refus VOLUME_TOO_LOW_FOR_GOAL (code de sortie 2)
```

Repli (exemples historiques, date figée au 2026-09-26) :

```bash
python -m plan_engine.cli examples/beginner_10k.json --as-of 2026-09-26
```

Affiche le plan en français : allures en fourchettes (min/km), semaines avec phase, km et séances.
Après `pip install -e .`, la commande `plan-engine` fait la même chose.

- `--as-of AAAA-MM-JJ` : date de référence (même entrée + même date → même plan).
- `--recent-km 11,10,12,11` : remplace les km des 4 dernières semaines (plus récente en dernier).
- `--json` : sortie JSON brute (plan ou erreur typée).

Codes de sortie : `0` plan produit, `2` plan refusé (erreur typée, message en français), `1` entrée invalide.

### Ordre de passage le soir de la démo

PlanOrch tranche à 14h30, selon que les correctifs P0-11 (volume et sortie longue de demo_1) et P0-12 (jour affiché avant la course) sont mergés ou non.

| Ordre | Quand | Passage |
| --- | --- | --- |
| **A** | P0-11 **et** P0-12 mergées | demo_1 → demo_2 → demo_3 → demo_4 |
| **B** (repli) | sinon | demo_2 → demo_3 → demo_4, puis demo_1 en dernier ou sauté |

Ordre B, prêt à copier :

```bash
python -m plan_engine.cli examples/demo/demo_2_intermediate_10k.json   # ouvre la démo : 10 km intermédiaire
python -m plan_engine.cli examples/demo/demo_3_advanced_half.json      # semi confirmé
python -m plan_engine.cli examples/demo/demo_4_undertrained_beginner_half.json  # refus en français, code 2
# demo_1 seulement s'il reste du temps et que P0-11 est mergée
```

Pendant la démo, on lance uniquement ces 4 fichiers, sans saisir `--recent-km` en direct.

## Documentation

- Architecture : [`docs/architecture.md`](docs/architecture.md)
- Exemples d’entrée : [`examples/`](examples/)
