# Template — Audit digital 1-pager (livré après OK du prospect)

## Règles invariantes

- **Longueur** : 1 page max, lecture en 10 minutes. On n'impressionne pas à la quantité.
- **Spécifique, pas générique** : chaque point cite une donnée réelle du resto. Pas de "les sites doivent être rapides", mais "votre site met 6.2 secondes à charger".
- **3 points forts / 3 faiblesses / 3 recos** : pas plus, pas moins. C'est lisible et actionnable.
- **Pas de pitch commercial dans l'audit** : la vente se fait en appel, pas dans le PDF. L'audit doit être utile en soi, y compris si le prospect choisit un concurrent.
- **Livraison** : email texte ou PDF simple. Pas besoin de design sophistiqué pour la V1 — on a dit 48h.

## Structure fixe

```markdown
# Audit digital — {{nom_resto}}

**Réalisé le {{date}} par Maïck, Mad Makers**
**Durée de lecture : 10 minutes**

---

## Ce que vous faites déjà bien (3 points)

### 1. {{point_fort_1_titre}}
{{point_fort_1_detail — phrase de 2-3 lignes avec données réelles}}

### 2. {{point_fort_2_titre}}
{{point_fort_2_detail}}

### 3. {{point_fort_3_titre}}
{{point_fort_3_detail}}

---

## Ce qui coûte des couverts aujourd'hui (3 points)

### 1. {{faiblesse_1_titre}}
**Impact estimé** : {{impact_1 — ex. "30% des visiteurs mobiles quittent avant de voir la carte"}}
{{faiblesse_1_detail_concret}}

### 2. {{faiblesse_2_titre}}
**Impact estimé** : {{impact_2}}
{{faiblesse_2_detail_concret}}

### 3. {{faiblesse_3_titre}}
**Impact estimé** : {{impact_3}}
{{faiblesse_3_detail_concret}}

---

## Ce que je ferais en priorité (3 recos)

### Priorité 1 — {{reco_1_titre}}
- **Ce qu'il faut faire** : {{reco_1_action}}
- **Effort** : {{reco_1_effort — ex. "2 jours de travail"}}
- **Gain estimé** : {{reco_1_gain — ex. "+15 réservations/mois"}}

### Priorité 2 — {{reco_2_titre}}
- **Ce qu'il faut faire** : {{reco_2_action}}
- **Effort** : {{reco_2_effort}}
- **Gain estimé** : {{reco_2_gain}}

### Priorité 3 — {{reco_3_titre}}
- **Ce qu'il faut faire** : {{reco_3_action}}
- **Effort** : {{reco_3_effort}}
- **Gain estimé** : {{reco_3_gain}}

---

## En résumé

{{résumé_2_phrases — ce qui est le plus urgent et pourquoi}}

Si vous voulez qu'on regarde ensemble comment mettre en place une de ces priorités, répondez simplement à cet email. Sans engagement.

Maïck — Mad Makers
{{from_email}} · {{landing_url}}
```

## Sources de données pour remplir l'audit

Pour chaque prospect, Claude doit aller chercher dans le batch JSON :

- `site_audit.url`, `site_audit.performance.mobile_score`, `site_audit.performance.lcp`
- `site_audit.has_ssl`, `site_audit.has_viewport`, `site_audit.generator`
- `site_audit.has_menu`, `site_audit.has_booking`
- `gmb_rating`, `gmb_reviews_count`, `gmb_phone`
- `ca_dernier` (pour dimensionner les gains en euros si info dispo)

Et surtout : lire le snapshot HTML sauvegardé dans `data/site_snapshots/{siret}.html`
pour pouvoir faire des remarques spécifiques sur le design, les photos, le menu, etc.

## Points forts usuels (à piocher selon le prospect)

- Bonne note Google (≥ 4.3 ★ avec ≥ 30 avis)
- Photos attrayantes sur GMB
- Fiche GMB bien renseignée (horaires, téléphone, site)
- Menu visible sur Google
- Site responsive (si c'est le cas)
- Bouton réservation TheFork/Resy intégré

## Faiblesses usuelles (à piocher selon le prospect)

- Pas de site → client potentiel va chez le concurrent qui a le menu en ligne
- Site lent mobile (< 40/100) → 50% d'abandon avant 3s
- Pas de HTTPS → alerte navigateur, perte de confiance
- Pas adapté mobile → 70% du trafic est mobile chez un resto
- Pas de bouton réservation → friction = réservation téléphone = personnel mobilisé
- Pas de menu visible → le client quitte pour aller voir ailleurs
- Photos de plats médiocres ou absentes → l'appétit passe par les yeux
- Pas de référencement local (GMB non optimisé) → absent du "restaurant près de moi"

## Recos usuelles (à piocher selon le prospect)

### Si pas de site
1. Site vitrine 1 page avec menu PDF + bouton réservation + photos → gain : 10-30 cov/mois
2. Fiche GMB complétée + 20 photos pro → gain : +40% de visibilité locale
3. Intégration TheFork/Resy → gain : cov directs sans appel

### Si site existe mais lent
1. Refonte légère sur Framer (sous 72h) → score mobile > 85/100
2. Compression photos + CDN → gain : -2s de chargement
3. Ajout bouton réservation flottant → +25% taux de conversion visiteur → covert

### Si site OK mais SEO faible
1. SEO local (balises, mots-clés "restaurant {{ville}}") → gain : +3 positions Google
2. Publication mensuelle d'articles courts (plats saisonniers) → trafic organique
3. Stratégie avis (20 avis frais par trimestre) → booster GMB
```
