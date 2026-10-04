# Nova

Assistante vocale personnelle pour Android, codée en Python et lancée via Termux.
Comprend des commandes locales (heure, batterie, stockage, fichiers, doublons, calculatrice)
et peut réfléchir librement grâce à l'API Gemini.

## Installation
1. Installer Termux (F-Droid recommandé) et Termux:API
2. `pkg install python termux-api`
3. Créer un fichier `.nova_cle` contenant une clé API Gemini gratuite (aistudio.google.com)
4. `python nova.py`
