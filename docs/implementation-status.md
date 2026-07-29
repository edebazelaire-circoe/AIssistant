# État d’implémentation par lot

| Tâche | Statut | Preuve principale |
|---|---|---|
| 00 Orchestration | Terminé | plan, ADR, rapport et gates |
| 01 Stack/squelette | Terminé | ADR 0001, pyproject, CI |
| 02 Contrats | Terminé | `domain/models.py` |
| 03 Architecture | Terminé | `scripts/check_architecture.py` |
| 04 Audio/états | Terminé | ring buffer, WebSocket audio, machine d’états |
| 05 Wake-word | Prototype fonctionnel | enrôlement local, score, suppression |
| 06 Transcription | Prototype + adaptateur optionnel | fixture partielle/finale, port Realtime |
| 07 Diarisation | Baseline fonctionnel | clusters anonymes, hints déterministes |
| 08 Session/timeline | Terminé | SQLite append-only, replay WebSocket |
| 09 Fournisseurs | Terminé | configs, rôles, diagnostics par étape |
| 10 Outils/connecteurs | Terminé | registries, runner, lifecycle events |
| 11 Politiques | Terminé | disabled/manual/automatic, token single-use |
| 12 Excel | Terminé | schema, match, safe write, verify, diff, preview |
| 13 update_roadmap | Terminé | plan, approval, auto, artifacts |
| 14 Orchestrateur | Prototype fonctionnel | routage déterministe et lecture contexte |
| 15 Profil réunion | Prototype fonctionnel | extraction et synthèse traçables |
| 16 Inspector shell | Terminé | UI responsive, replay/reconnect |
| 17 Audio/transcript UI | Terminé | capture, wake samples, transcript speakers |
| 18 Plan/outils/résultats UI | Terminé | approvals, timeline, Excel preview/rollback |
| 19 Réglages | Terminé pour V1 | voix, racine, politique, modèles/diagnostics |
| 20 E2E/release | Terminé avec limites documentées | tests, scénario, package zip |
