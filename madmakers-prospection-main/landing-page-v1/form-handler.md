# Setup du formulaire — Formspree (5 minutes, gratuit)

Le formulaire de la landing envoie les infos de qui a cliqué "Audit gratuit" dans la boîte mail Mad Makers. On utilise **Formspree** pour ne pas avoir à coder un backend.

## Étapes

1. Va sur **https://formspree.io/** et crée un compte gratuit avec `contact@<ton-domaine>`.
2. Clique sur **+ New Form**.
3. Nomme le form "Audit Restaurants Mad Makers", destination email = `contact@<ton-domaine>`.
4. Formspree te donne un **form ID** du style `xayzq123`.
5. Ouvre `landing-page-v1/index.html` et cherche `MONFORMSPREEID` (dans la ligne `action="https://formspree.io/f/MONFORMSPREEID"`).
6. Remplace par ton ID : `action="https://formspree.io/f/xayzq123"`.
7. Push le changement sur GitHub. GitHub Pages redéploie automatiquement la landing en 1-2 min.

## Plan gratuit

Jusqu'à **50 submissions/mois**. Si Mad Makers dépasse (= plus de 50 audits demandés/mois → très bonne nouvelle), passer au plan Basic 10$/mois pour submissions illimitées.

## Ce qui se passe quand quelqu'un remplit le form

1. Formspree reçoit la soumission.
2. Formspree envoie un email à `contact@<ton-domaine>` avec : prénom, nom resto, ville, email, site (facultatif).
3. Maïck reçoit l'email dans sa boîte.
4. Il l'ajoute manuellement dans Folk (copier-coller 30 secondes) avec le tag `inbound-landing`.
5. Il lance le skill `/madmakers-prospection` pour générer l'audit personnalisé de ce prospect (on saute l'étape sourcing, on démarre direct à l'étape audit).

## Anti-spam

Formspree inclut un captcha par défaut. Si du spam passe, activer reCAPTCHA dans les settings du form.
