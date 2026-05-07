# Routine quotidienne — Mad Makers Prospection

**Objectif** : 30 contacts par jour, 5 jours par semaine = 150/semaine = 600/mois.

**Temps requis** : 30 min le matin + 15 min en fin de journée.

---

## Matin (30 min, 9h-9h30)

1. **Ouvre Terminal + active le venv** :
   ```bash
   cd ~/Documents/madmakers-prospection
   source .venv/bin/activate
   ```

2. **Lance Claude Code** dans le dossier et tape :
   ```
   /madmakers-prospection
   ```

3. **Laisse Claude tourner** les étapes 1-3 (source + enrich). Tu peux aller te faire un café, ça prend 8-10 min total.

4. **Étape 4 — Revue des emails** (10 min). Claude te présente les emails par batch de 5. Pour chacun :
   - Lis le corps
   - Vérifie que le signal est juste (pas d'hallucination sur un détail du site)
   - Édite si un truc cloche — tu peux juste dire à Claude "reformule le 3 de manière moins formelle"
   - Valide

5. **Étape 5 — Enrichissement manuel des emails** (5 min). Le batch a des dirigeants identifiés mais pas d'emails pro. Pour chaque prospect :
   - Regarde dans Folk s'il a déjà un email (si un prospect a déjà été ajouté par la landing par exemple)
   - Sinon, va sur Google : `"prenom nom" nomresto.com` → tu trouves souvent l'email du dirigeant dans les mentions légales de leur site ou sur LinkedIn
   - Ajoute l'email dans Folk
   - Alternative : utiliser Dropcontact (39€/mois) quand le volume justifie

6. **Étape 6 — Drafts Gmail** : Claude crée les drafts. Ouvre Gmail Mad Makers, vérifie les brouillons, **clique Envoyer** par lot.

7. **Étape 7 — Export Folk** : Claude a produit un CSV. Import dans Folk en 30 secondes.

---

## Fin de journée (15 min, 17h-17h15)

1. **Gmail Mad Makers** → check les réponses reçues.
2. **Pour chaque réponse positive** (intéressé par l'audit) :
   - Passe le contact dans Folk du groupe "Prospects resto" → "Leads chauds"
   - Lance `/madmakers-prospection audit <siret>` pour générer l'audit complet
   - Programme un appel téléphonique dans la foulée (pas par email — le tel est 3x plus converti sur du TPE)
3. **Pour chaque réponse négative** (pas intéressé) :
   - Passe le contact en "Dormants"
   - Note la raison dans Folk (pas envie, trop cher, a déjà une agence, etc.)
4. **Pour chaque no-reply** :
   - Laisse tel quel, la relance J+4 est déjà programmée par cron

---

## Une fois par semaine (vendredi 17h, 20 min)

```
/madmakers-prospection debrief
```

Claude te sort :
- Nb contacts envoyés cette semaine
- Nb réponses
- Taux de réponse par signal (sans_site vs site_obsolete vs gmb_actif)
- Nb RDV / nb deals
- Ajustement ICP proposé s'il détecte un signal sous-exploité

Tu valides ou tu dis "je veux pas changer cette semaine".

---

## Garde-fous

- **30 contacts/jour max**. Si tu poses plus, tu brûles ta délivrabilité Gmail. Mieux vaut 30 quali que 100 cramés.
- **Relance J+4 et J+10 uniquement**. Au-delà, c'est du harcèlement et ça brûle la marque.
- **Jamais envoyer pendant le service** (entre 11h et 14h30 ou 18h et 22h). Le dirigeant lit après coup et ça finit à la poubelle. Programme les envois Gmail pour 9h ou 15h.
- **Si un prospect répond "stop" ou "unsubscribe"** : bascule direct en "Dormants" et ne retente plus jamais. RGPD + réputation.

---

## KPIs hebdo à viser (extraits du BP)

| KPI | Seuil M1 | Cible M3 |
|---|---|---|
| Prospects envoyés / semaine | 150 (30 × 5j) | 150 |
| Taux de réponse | 5% | 10-15% |
| Taux conversion demo → deal | 10% | 15-20% |
| Deals closés / mois | 1-2 | 4-6 |

Si à M2 tu es à 3% de réponse, c'est que les emails ne marchent pas : change la variante d'accroche ou le pricing, pas le volume.
