# Guide opérateur

## États

- **MIC_OFF** : aucune frame acceptée, buffer vidé.
- **STANDBY** : capture et wake-word locaux uniquement.
- **TRANSCRIBING** : la transcription distante est autorisée si un adaptateur est configuré ; le prototype reste silencieux.
- **INTERACTIVE** : questions et capacités peuvent être routées.
- **ERROR_RECOVERABLE** : état réservé aux diagnostics récupérables.

Le bouton d’arrêt d’urgence force `MIC_OFF` et vide immédiatement le buffer.

## Sécurité Excel

Le connecteur n’opère que sous la racine autorisée. Il refuse les chemins traversants, les schémas ambigus, les lignes ambiguës et les fichiers modifiés entre preview et validation. Une copie temporaire est écrite, rouverte et vérifiée avant remplacement atomique. Un backup est conservé pour les tests et un rollback est exposé dans l’Inspector.

## Wake-word

Enregistrer plusieurs variantes courtes dans un environnement calme. Le détecteur compare une signature spectrale locale sur une fenêtre glissante. Ajuster le seuil prudemment : un seuil bas augmente les faux réveils. Aucun audio d’enrôlement brut n’est persisté ; seule une feature normalisée est stockée.

## Modèles

La page Modèles sépare : secret présent, authentification, projet/compte, quota, accès au modèle, compatibilité de rôle et transport Realtime. L’inventaire HTTP ne prouve pas à lui seul que le handshake Realtime est autorisé.
