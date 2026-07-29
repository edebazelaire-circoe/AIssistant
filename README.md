# Jarvis Agent Inspector V1

Prototype local-first d’assistant de réunion, centré sur un **Agent Inspector** observable. Il couvre la machine d’états, le buffer audio local, un wake-word enrôlable expérimental, une transcription/diarisation de démonstration, les sessions rejouables, les fournisseurs de modèles, les politiques de capacités et un scénario Excel réellement muté et vérifié.

## Démarrage

```bash
python -m pip install -e ".[dev]" --no-build-isolation
python scripts/create_demo_workbook.py
python -m jarvis_agent.web.api
```

Ouvrir ensuite `http://127.0.0.1:8765`. Le flag `--no-build-isolation` rend aussi l’installation possible dans un environnement interne sans miroir de build ; il peut être omis sur un poste disposant d’un index PyPI complet.

## Scénario de référence

1. Passer de **Micro coupé** à **Veille locale**.
2. Démarrer une réunion.
3. Injecter deux phrases avec deux locuteurs.
4. Injecter : `L’action Sécuriser le portail client est terminée.`
5. En politique manuelle, inspecter puis approuver le changement.
6. Vérifier le plan, les appels outils, la cellule modifiée, le preview et le fichier produit.
7. Répéter avec la politique automatique.

Le scénario en ligne de commande est disponible avec :

```bash
PYTHONPATH=src python scripts/run_reference_scenario.py
```

## OpenAI / GPT‑Live

L’architecture ne fige aucun modèle. Les secrets restent dans l’environnement et l’Inspector persiste uniquement une référence telle que `OPENAI_API_KEY`. Au 29 juillet 2026, GPT‑Live est annoncé pour ChatGPT mais pas encore exposé dans l’API ; la configuration OpenAI doit donc pointer vers un modèle Realtime effectivement disponible pour le projet et être vérifiée par les diagnostics.

Le mode local de démonstration fonctionne sans clé. L’adaptateur `OpenAIRealtimeTranscriptionAdapter` est isolé et configurable, mais le flux réseau réel dépend des droits, du modèle et du contrat d’événements disponibles au moment du test.

## Limites assumées du prototype

- Le wake-word spectral est un baseline transparent d’enrôlement local, pas un détecteur production.
- La diarisation audio est un clustering de features minimal ; les fixtures avec `speaker_hint` donnent un scénario déterministe.
- Le navigateur envoie du PCM au service local. En `STANDBY`, aucun adaptateur distant n’est appelé.
- L’analyse de réunion locale est déterministe. Un modèle d’analyse peut être ajouté derrière le rôle `analysis`.
- L’application est une web app localhost, pas encore un binaire Electron/Tauri.

## Qualité

```bash
python scripts/check_architecture.py
pytest
```

Les tests couvrent les transitions, le buffer, le store rejouable, l’enrôlement, les diagnostics, les politiques, l’écriture Excel sûre, les ambiguïtés, l’idempotence et les scénarios manuel/automatique.
