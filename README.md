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

```bash
python -m plan_engine.cli examples/beginner_10k.json --as-of 2026-09-26
```

Affiche le plan en français : allures en fourchettes (min/km), semaines avec phase, km et séances.
Après `pip install -e .`, la commande `plan-engine` fait la même chose.

- `--as-of AAAA-MM-JJ` : date de référence (même entrée + même date → même plan).
- `--recent-km 11,10,12,11` : remplace les km des 4 dernières semaines (plus récente en dernier).
  Exemple : `python -m plan_engine.cli examples/beginner_half.json --recent-km 11,10,12,11` → plan refusé
  (`VOLUME_TOO_LOW_FOR_GOAL`) une fois le plafond P0-4 mergé.
- `--json` : sortie JSON brute (plan ou erreur typée).

Codes de sortie : `0` plan produit, `2` plan refusé (erreur typée, message en français), `1` entrée invalide.

## Documentation

- Architecture : [`docs/architecture.md`](docs/architecture.md)
- Exemples d’entrée : [`examples/`](examples/)
