# Template — Relances J+4 et J+10

## Principe

- **J+4** : rappel court, référence concrète à l'email initial, pas d'ajout de pression.
- **J+10** : dernière relance. On change d'angle : on donne un mini-insight gratuit pour laisser une valeur même en cas de non-réponse.
- **Pas de J+20** en V1. Si pas de réponse à J+10, on archive en "Dormant" dans Folk et on arrêt.

## Règles de relance

- **Thread** : toujours en réponse au thread initial (même objet, même fil). Jamais un nouvel email.
- **Longueur** : 40-70 mots max.
- **Interdit** : "Bonne réception de mon précédent email", "Je me permets de relancer", "Je n'ai pas eu de nouvelles".
- **Signal d'exit gracieux** : la J+10 propose toujours une porte de sortie ("Si c'est pas le moment, aucun souci, je te laisse tranquille").

---

## J+4 — Relance courte

### Variante 1 — Relance "factuelle" (par défaut)

> Objet : (même thread, pas de nouvel objet)
>
> Salut {{prenom_dirigeant}},
>
> J'imagine que la semaine a été chargée. Je te remets le lien vers ce que j'ai préparé pour {{nom_resto}} — il reste sous le coude, prêt à partir dès ton go.
>
> Tu préfères que je te l'envoie directement, ou on se parle 15 min avant ?
>
> Maïck

### Variante 2 — Relance "insight" (si on a détecté un fait nouveau)

Exemple si tu repères un changement (avis récent critique, nouvelle ouverture concurrent, etc.)

> Salut {{prenom_dirigeant}},
>
> En re-regardant ta fiche j'ai vu {{fait_nouveau — ex. "3 avis récents qui mentionnent la difficulté à réserver en ligne"}}. Ça renforce ce que je te disais dans mon email. Je t'envoie l'audit si tu dis oui, 30 secondes.
>
> Maïck

---

## J+10 — Relance finale avec valeur

> Objet : (même thread)
>
> Salut {{prenom_dirigeant}},
>
> Dernière relance, promis. Je comprends si ce n'est pas le moment.
>
> Avant de te laisser tranquille, un truc que j'ai remarqué qui te prendra 2 minutes à corriger et qui compte : {{mini_insight_gratuit — ex. "ton numéro de téléphone n'est pas cliquable sur ta fiche Google depuis mobile, du coup chaque réservation téléphone = le client doit recopier le numéro"}}.
>
> Si un jour tu veux creuser le reste, ma porte est ouverte. Bonne continuation avec {{nom_resto}}.
>
> Maïck — Mad Makers

---

## Mini-insights gratuits (pour la J+10)

Un reservoir d'insights courts et vérifiables, à piocher selon ce qu'on a vu dans l'audit :

- **Téléphone non cliquable mobile** → "Un clic sur ton numéro Google Maps devrait lancer l'appel. Vérifie depuis ton iPhone, beaucoup de restos perdent cette fonction."
- **Horaires pas à jour GMB** → "Tes horaires affichent encore [ancienne config]. Google pénalise les fiches pas à jour, ça te sort des résultats 'ouvert maintenant'."
- **Photos anciennes** → "Les 3 premières photos Google datent de 2021. Remplace-les par 3 photos de l'assiette actuelle prises au smartphone, ça booste le CTR fiche."
- **Réponses aux avis** → "Tu réponds à 2 avis sur 10. Un resto qui répond à 80% des avis monte dans le ranking local de Google."
- **Menu PDF ancien** → "Ton menu PDF daté de 2023. Le remplacer par la version à jour fait gagner 5% de conversion visiteur → réservation."
- **Pas de bouton réservation** → "Ajoute un bouton TheFork sur ta fiche GMB (gratuit, 5 min). Tu vas prendre des covers sans que le téléphone sonne."

Les insights doivent être **vrais et vérifiables**. Claude doit aller voir le snapshot HTML ou la fiche GMB avant de balancer l'insight.
