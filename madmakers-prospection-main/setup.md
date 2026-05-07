# Setup Mad Makers Prospection — Guide pas-à-pas pour Maïck

Ce guide t'amène de zéro à "je lance mon premier batch" en **2 à 3 heures** (création de comptes comprises). Tu n'as rien besoin de savoir en développement. Si un truc plante, demande à Claude Code directement : "j'ai ce message d'erreur, aide-moi" — il a tout le contexte du projet.

## Ce que tu vas installer et créer

| Composant | Rôle | Coût | Temps setup |
|---|---|---|---|
| Python 3.11+ | pour lancer les scripts | 0 | 5 min |
| uv | gestionnaire de packages Python | 0 | 2 min |
| GitHub repo clone | récup du code | 0 | 2 min |
| Google Workspace | email pro `contact@tondomaine` | 6€/mois | 30 min |
| INSEE SIRENE API | données entreprises gratuites | 0 | 10 min |
| Google Cloud + Places API + PageSpeed | détection GMB + perf sites | ~10-20€/mois | 20 min |
| Pappers API | enrichissement dirigeants | 0 (freemium) | 5 min |
| Folk CRM | suivi contacts | 30€/mois | 15 min |
| Formspree | form de la landing | 0 | 5 min |
| Domaine + OVH | `tondomaine.fr` | 10€/an | 15 min |

**Total coûts fixes mensuels** : ~50€/mois (≈ moins que le budget stack prévu dans le BP).

---

## Étape 1 — Python + uv

### Sur Mac

Ouvre **Terminal** (Applications → Utilitaires → Terminal) et tape :

```bash
# Vérifie si Python est déjà installé
python3 --version
```

Si la version est < 3.11 ou si la commande dit "not found" :
```bash
# Installe Homebrew si tu ne l'as pas
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Puis Python
brew install python@3.11
```

Puis installe `uv` (gestionnaire de packages moderne, plus simple que pip) :
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Redémarre Terminal pour que `uv` soit reconnu.

---

## Étape 2 — Cloner le repo

Goudet t'a envoyé un lien GitHub du style `https://github.com/goudetabale/madmakers-prospection`.

1. Accepte l'invitation (email de GitHub dans ta boîte).
2. Dans Terminal :
```bash
cd ~/Documents
git clone https://github.com/goudetabale/madmakers-prospection.git
cd madmakers-prospection
```

Tu es maintenant dans le dossier du projet.

---

## Étape 3 — Installer les dépendances Python

```bash
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

Tu devrais voir `Installed X packages`. C'est bon.

**À refaire chaque fois que tu ouvres un nouveau Terminal** :
```bash
cd ~/Documents/madmakers-prospection
source .venv/bin/activate
```

---

## Étape 4 — Domaine + Google Workspace

### 4a. Acheter le domaine

1. Va sur **https://www.ovh.com/fr/**
2. Cherche le domaine que tu veux (`madmakers.fr`, `.agency`, `.com`...) — environ 10€/an pour le .fr
3. Achète-le. Tu recevras un email avec tes identifiants OVH.

### 4b. Google Workspace

1. Va sur **https://workspace.google.com/**
2. Clique "Commencer". Essai 14 jours gratuit puis 6€/mois.
3. Choisis "J'ai déjà un domaine" et entre ton domaine OVH.
4. Google te guide pour connecter le domaine (il te donne des enregistrements MX à ajouter chez OVH — 10 min de manip).
5. Crée l'adresse `contact@tondomaine.fr`.

**Teste** : envoie-toi un email depuis ton Gmail perso vers `contact@tondomaine.fr`. Doit arriver dans Gmail Mad Makers.

### 4c. Connecte Gmail Mad Makers à Claude Code

Dans Claude Code, tape `/` pour voir les slash commands, cherche un truc lié à "connector" ou "mcp". Si pas visible, utilise le menu Claude Code → Settings → Connectors → Gmail → "Connect account" et choisis le compte `contact@tondomaine.fr`.

⚠️ Claude doit avoir accès UNIQUEMENT au compte Mad Makers, pas à ton Gmail perso. Sinon les drafts risquent de partir de la mauvaise adresse.

---

## Étape 5 — INSEE SIRENE API (gratuit)

1. Va sur **https://api.insee.fr/catalogue/**
2. Crée un compte (gratuit).
3. Dans "Mes applications" → "Créer une application".
4. Nomme-la "Mad Makers Prospection".
5. Souscris à l'API **"Sirene - V3.11"**.
6. Copie les deux clés : **Consumer Key** et **Consumer Secret**.

---

## Étape 6 — Google Cloud (Places + PageSpeed)

1. Va sur **https://console.cloud.google.com**
2. Crée un projet "Mad Makers".
3. Active ton compte de facturation (Google demande une CB — ne te fais pas avoir, les quotas gratuits couvrent largement la V1).
4. **Dans "APIs & Services" → "Library"** :
   - Active **"Places API (New)"**
   - Active **"PageSpeed Insights API"**
5. **Dans "APIs & Services" → "Credentials"** → "Create credentials" → "API key".
6. Copie la clé. **Important** : clique "Restrict key" → Restrictions API → coche uniquement "Places API (New)" et "PageSpeed Insights API". Ça évite qu'un leak de clé te coûte de l'argent.
7. **Budget** : va dans "Billing" → "Budgets & alerts" → "Create budget" → fixe 30€/mois avec alerte à 50%. Tu ne pourras pas dépasser sans le savoir.

---

## Étape 7 — Pappers API (gratuit)

1. Va sur **https://www.pappers.fr/api**
2. Crée un compte, clique "Obtenir une clé API gratuite".
3. Copie la clé. Plan gratuit = 500 requêtes/mois = 500 prospects enrichis/mois. Largement assez pour M1-M2.

---

## Étape 8 — Folk CRM

1. Va sur **https://folk.app**
2. Crée un workspace "Mad Makers" (pas le même que si tu en as un perso).
3. Plan "Standard" à 25€/mois (ou essai 14j).
4. Crée les groupes de contacts :
   - **"Prospects resto"** : le pipe principal
   - **"Leads chauds"** : ceux qui ont répondu
   - **"Clients actifs"**
   - **"Dormants"** : archivés sans réponse après J+10
5. Champs personnalisés à ajouter : `SIRET`, `Score ICP`, `Signal`, `Séquence`, `Étape`, `Statut`, `Date ajout`.

---

## Étape 9 — Formspree (form de la landing)

Suivre `landing-page-v1/form-handler.md`.

---

## Étape 10 — Remplir `.env`

Dans le dossier du projet, copie le template :
```bash
cp config/.env.example .env
```

Ouvre `.env` dans un éditeur (TextEdit, VS Code, etc.) et remplis **chaque clé** avec ce que tu as récupéré aux étapes 5-7.

Exemple :
```
INSEE_API_KEY=abcdef123456
INSEE_API_SECRET=xyz789
GOOGLE_API_KEY=AIzaSy...
PAPPERS_API_KEY=1234567890abcdef
MADMAKERS_FROM_NAME=Maïck — Mad Makers
MADMAKERS_FROM_EMAIL=contact@madmakers.fr
MADMAKERS_LANDING_URL=https://madmakers.fr/restaurants
MADMAKERS_PHONE=+33 6 XX XX XX XX
```

Sauvegarde. Ce fichier n'est jamais push sur GitHub (il est dans `.gitignore`).

---

## Étape 11 — Test de la config

Dans Terminal (venv activé) :
```bash
python scripts/config.py
```

Tu dois voir :
```
ROOT: /Users/maick/Documents/madmakers-prospection
ENV loaded: True
ICP niche: Restaurant traditionnel
ICP zones: ['Landes', ...]
FROM: Maïck — Mad Makers <contact@madmakers.fr>
INSEE_API_KEY: OK
GOOGLE_API_KEY: OK
PAPPERS_API_KEY: OK
```

Si une clé est `MANQUANT`, édite `.env` et recommence.

---

## Étape 12 — Activer le skill dans Claude Code

Pour que `/madmakers-prospection` soit reconnu par ton Claude Code personnel :

```bash
# Crée un symlink vers le skill
mkdir -p ~/.claude/commands
ln -s ~/Documents/madmakers-prospection/SKILL.md ~/.claude/commands/madmakers-prospection.md
```

Redémarre Claude Code. Tape `/` dans le chat, tu dois voir `/madmakers-prospection` dans la liste.

---

## Étape 13 — Premier lancement

Dans Claude Code, tape :
```
/madmakers-prospection
```

Claude va te guider. Pour le premier test, lance avec un petit volume pour vérifier que tout marche :
```
Lance un batch de test avec --limit 5 sur le département 40 seulement
```

Si ça plante à une étape, copie-colle le message d'erreur dans Claude Code — il saura quoi faire.

---

## Ce que tu fais ensuite chaque jour

Voir `daily_playbook.md`. Spoiler : 30 minutes le matin, tu as 30 drafts Gmail prêts à envoyer après relecture.

---

## En cas de galère

- **Message d'erreur que tu ne comprends pas** → copie-le dans Claude Code et demande.
- **Un script qui tourne en boucle** → Ctrl+C dans Terminal pour l'arrêter.
- **Une clé API qui ne marche plus** → vérifie si le compte a atteint le quota gratuit (surtout Pappers 500/mois).
- **Gmail rejette la création de draft** → vérifie que le bon compte est connecté dans Claude Code.

Et si vraiment rien n'avance, ping Goudet sur WhatsApp avec capture d'écran.
