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

## Documentation

- Architecture : [`docs/architecture.md`](docs/architecture.md)
- Exemples d’entrée : [`examples/`](examples/)
