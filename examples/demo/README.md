# Inputs de démo QA (as_of_date 2026-10-02)

Quatre `PlanRequest` pour la répétition QA. Les dates sont ancrées sur
`options.as_of_date: "2026-10-02"` : le plan part le lundi 2026-10-05
(course un dimanche, `days_to_race >= WEEKS×7 − 3`).

| Profil | Fichier | Résultat attendu |
| --- | --- | --- |
| 1 · débutant 5 km | [`demo_1_beginner_5k.json`](demo_1_beginner_5k.json) | Plan généré (10 semaines) |
| 2 · intermédiaire 10 km | [`demo_2_intermediate_10k.json`](demo_2_intermediate_10k.json) | Plan généré (11 semaines) |
| 3 · confirmé semi | [`demo_3_advanced_half.json`](demo_3_advanced_half.json) | Plan généré (12 semaines) |
| 4 · débutant sous-entraîné, semi | [`demo_4_undertrained_beginner_half.json`](demo_4_undertrained_beginner_half.json) | Refus `VOLUME_TOO_LOW_FOR_GOAL` |

Les 9 exemples `examples/*.json` restent inchangés (date de repli planner / conftest : 2026-09-26).

Ordre de passage : A (demo_1 en premier) si P0-11 et P0-12 sont mergées, sinon B (ouverture sur demo_2, demo_1 en dernier ou sauté). Voir « Ordre de passage le soir de la démo » dans le [README](../../README.md).
