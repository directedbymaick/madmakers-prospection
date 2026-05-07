# Landing Page V1 — Mad Makers

Page unique HTML + Tailwind (via CDN), sans build. Hébergée sur GitHub Pages.

## Déployer sur GitHub Pages (5 minutes)

1. Push le repo sur GitHub.
2. Dans les settings du repo : **Pages** → **Source** : "Deploy from a branch" → **Branch : main**, **Folder : /landing-page-v1**.
3. Save. GitHub te donne une URL du style `https://<ton-user>.github.io/<repo>/`.
4. Si tu as un domaine custom (ex : `madmakers.fr`) :
   - Dans les settings Pages : "Custom domain" = `madmakers.fr`.
   - Chez ton registrar (OVH), ajoute un CNAME qui pointe vers `<ton-user>.github.io`.
   - GitHub provisionne SSL automatiquement (attendre 10 min).

## Customiser

Tout est dans `index.html`. Pour changer :

- **Le nom** : remplacer "Mad Makers" partout (4 occurrences).
- **Les couleurs** : dans la balise `<script>` en haut, section `extend.colors`. `accent` = `#d84315` (terracotta), change pour ta palette.
- **Les tarifs** : section "pricing teaser", 3 cartes.
- **Le form** : voir `form-handler.md` pour remplacer `MONFORMSPREEID`.

## Roadmap V2

- Remplacer par une version Framer avec 3 vrais cas clients en screenshots.
- Ajouter une section "Ils nous ont fait confiance" quand 3 logos sont disponibles.
- Ajouter un blog pour SEO local (articles "Restaurants {ville} — pourquoi avoir un site").
