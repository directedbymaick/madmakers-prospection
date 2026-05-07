# Template — Cold email restaurants

## Règles invariantes

- **Longueur** : 80 à 130 mots maximum. On veut qu'il soit lu en entier.
- **Ton** : direct, concret, parler au propriétaire, jamais "Bonjour Madame/Monsieur". On cite son resto par son nom.
- **Pas d'anglicismes marketing** : pas de "stratégie d'acquisition", "conversion funnel", "growth". Le propriétaire de resto veut plus de couverts, pas une leçon de digital.
- **Preuve > promesse** : on ouvre avec un constat vérifié sur SON site ou son absence de site. Pas de généralités.
- **CTA unique** : l'audit gratuit. Pas "réponse", pas "appel", pas "on se fait un café". Juste : je t'envoie l'audit si tu dis oui.
- **Signature** : Maïck seulement. Pas "Cordialement", trop froid.

## Structure

1. **Objet** — 5 à 8 mots, concret, pas générique. Mentionner le resto ou sa ville.
2. **Ouverture (1 phrase)** — le constat factuel qui montre qu'on a regardé.
3. **Implication (1-2 phrases)** — ce que ça lui coûte concrètement (covers ratés, réservations téléphone qui prennent du temps, etc.).
4. **Proposition (1-2 phrases)** — audit gratuit 10 min de lecture, livré en 48h. Zéro engagement.
5. **CTA** — "Tu veux que je te l'envoie ?"
6. **Signature** — prénom + signature mail avec lien landing.

## Variantes d'accroche selon le signal détecté

### Signal : **sans_site** (pas de site web du tout)
> Objet : {{nom_resto}} — pas de site, c'est voulu ?
>
> Salut {{prenom_dirigeant}},
>
> Je suis tombé sur {{nom_resto}} en cherchant où manger à {{ville}} ce week-end. Tes avis Google sont excellents ({{gmb_rating}}★ sur {{gmb_reviews_count}} avis) mais aucun site web en vue. Résultat : ton client potentiel clique ailleurs pour voir la carte.
>
> J'ai préparé un audit 1 page qui montre exactement ce qu'un site de réservation te rapporterait en couverts supplémentaires — basé sur tes données réelles, pas sur des moyennes sectorielles.
>
> Tu veux que je te l'envoie ?
>
> Maïck — Mad Makers
> {{landing_url}}

### Signal : **site_obsolete** (site existant mais score perf mobile < 40 ou pas HTTPS)
> Objet : {{nom_resto}} — ton site charge en {{lcp_seconds}}
>
> Salut {{prenom_dirigeant}},
>
> J'ai testé {{nom_resto}}.fr sur mon iPhone ce matin. Il met {{lcp_seconds}} à se charger, {{reason_obsolete}}. 80% de tes visiteurs ferment avant de voir la carte.
>
> Je te propose un audit 1 page avec les 3 corrections prioritaires (et ce que chacune rapporterait en réservations). 10 min de lecture, gratuit, pas de vente dedans.
>
> Je te l'envoie ?
>
> Maïck — Mad Makers
> {{landing_url}}

### Signal : **gmb_actif_site_moyen** (GMB très actif, site convenable mais perfectible)
> Objet : {{nom_resto}} — {{gmb_reviews_count}} avis et...
>
> Salut {{prenom_dirigeant}},
>
> {{nom_resto}} a {{gmb_reviews_count}} avis Google, moyenne {{gmb_rating}}★ — tu fais clairement bien le job en salle. Côté visibilité en ligne par contre, 2-3 choses me sautent aux yeux qui coûtent probablement des covers sans que tu le voies.
>
> J'ai préparé un audit 1 page, uniquement sur ton cas, avec 3 recos concrètes. Gratuit, 10 min de lecture, zéro démarchage après.
>
> Ça t'intéresse ?
>
> Maïck — Mad Makers
> {{landing_url}}

## Placeholders disponibles (à remplir par Claude)

- `{{nom_resto}}` : `gmb_name` ou `nom_commercial` ou `raison_sociale`
- `{{ville}}` : `ville`
- `{{prenom_dirigeant}}` : première partie de `dirigeant_nom` (si connu, sinon "Salut," tout court)
- `{{gmb_rating}}` : `gmb_rating`
- `{{gmb_reviews_count}}` : `gmb_reviews_count`
- `{{lcp_seconds}}` : `site_audit.performance.lcp` ou estimation
- `{{reason_obsolete}}` : formulation humaine du pb principal ("pas de HTTPS", "pas adapté mobile", "design de 2012")
- `{{landing_url}}` : from env `MADMAKERS_LANDING_URL`
- `{{from_name}}` : from env `MADMAKERS_FROM_NAME`

## Ce qu'il NE FAUT JAMAIS faire

- Pas de "J'espère que ce mail vous trouve bien"
- Pas de "Notre agence vous accompagne"
- Pas de liste à puces façon brochure commerciale
- Pas de "Temps de réponse garanti sous 24h"
- Pas de mention du prix dans le cold email
- Pas de pièce jointe (l'audit arrive après le OK)
