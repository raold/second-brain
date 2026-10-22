# apple-brain — ton Second Brain avec Apple Intelligence

Outil en ligne de commande `brain`, 100 % local et gratuit : il indexe le coffre Obsidian
« Second Brain » (iCloud) et utilise le modèle **Apple Intelligence on-device**
(framework Foundation Models de macOS 27) pour répondre, chercher et ranger.

| Brique | Techno Apple utilisée |
| --- | --- |
| Réponses et classement | `FoundationModels` — modèle on-device (contexte 8 192 tokens, français) |
| Recherche par le sens | `NaturalLanguage` — `NLContextualEmbedding` (on-device) |
| Recherche par mots-clés | SQLite FTS5 (BM25), sans accents |
| PDF / images | `PDFKit`, `Vision` (OCR on-device) |
| Fichiers par nom | Spotlight (`mdfind`) |

Rien ne sort du Mac, aucune clé d'API.

## Commandes

```bash
brain ask "Quelle est la date limite pour la mobilité hors Erasmus ?"
brain chat                         # questions en boucle
brain search "responsabilité délictuelle" -n 5
brain find "TOEFL"                 # fichiers et dossiers par nom
brain organize                     # plan de rangement : racine du coffre + Inbox/
brain organize ~/Downloads         # propose où classer tes téléchargements dans le coffre
brain organize --apply             # déplace les propositions de confiance « haute »
brain mv "note.md" "Routine/Idées" # déplacement manuel avec mise à jour des liens
brain undo                         # annule le dernier lot de déplacements
brain index                        # mise à jour incrémentale (automatique toutes les 30 min)
brain status
```

## Comment ça marche

- **ask** : Apple Intelligence génère d'abord des mots-clés (synonymes FR/EN), puis la
  recherche hybride (BM25 + embeddings, fusion RRF) sélectionne les passages qui tiennent
  dans le contexte du modèle. Le modèle répond *uniquement* à partir de ces extraits et cite
  `[n]`. La récupération est faite par le code et non laissée au modèle : le petit modèle
  on-device appelle mal les outils et invente sinon.
- **organize** : pour chaque fichier, les embeddings présélectionnent ~12 dossiers du coffre
  dont le contenu ressemble ; Apple Intelligence choisit parmi eux (génération guidée,
  impossible d'inventer un dossier) en suivant le plan de classement de `AGENTS.md`.
  Rien n'est déplacé sans `--apply`, jamais d'écrasement, `raw/` n'est jamais déplacé,
  les liens `[[dossier/Note]]` et `[x](dossier/Note.md)` sont mis à jour, et chaque lot est
  journalisé pour `brain undo`. Le graphe graphify est reconstruit après chaque lot.

## Intégrations

- **Claude Code / Claude Desktop** : `brain mcp` est un serveur MCP (outils
  `search_second_brain`, `ask_apple_intelligence`, `find_files`, `organize_plan`,
  `move_item`, `reindex`).
- **Siri / Spotlight / barre des menus** : `shortcut/Second Brain.shortcut` (Raccourci qui
  demande la question puis lance `brain ask`). Après import, activer une fois
  Raccourcis › Réglages › Avancé › « Autoriser l'exécution de scripts ».
  Ensuite : « Dis Siri, Second Brain ».
- **Index automatique** : LaunchAgent `com.eliotvillaudy.applebrain.index`
  (copie dans ce dossier).

## Fichiers

- Binaire : `~/.local/bin/brain`
- Index : `~/Library/Application Support/AppleBrain/index.sqlite` (hors iCloud)
- Journal des déplacements : `~/Library/Application Support/AppleBrain/moves.jsonl`
- Autre coffre : `BRAIN_VAULT=/chemin brain …`

## Recompiler

```bash
swift build -c release && cp .build/release/brain ~/.local/bin/brain
```

Requiert macOS 27, un Mac Apple Silicon et Apple Intelligence activé
(Réglages Système › Apple Intelligence et Siri).
