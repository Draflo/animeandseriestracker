# Projet : Suivi anime

## Objectif
Suivi personnel des anime en cours et terminés, avec historique pour alimenter
des suggestions, et détection des sorties/annonces à surveiller.

## Fichiers du dossier

| Fichier                        | Rôle                                                              |
|---------------------------------|--------------------------------------------------------------------|
| `anime-data.json`                | Source de vérité. C'est le SEUL fichier à éditer pour changer des infos. |
| `anime-tracker.template.html`    | Squelette visuel. Ne jamais modifier à la main sauf demande explicite de design. |
| `generate.py`                    | Génère `anime-tracker.html` à partir du JSON + du template. Utilisé aussi bien en local que par le build Cloudflare. |
| `anime-tracker.html`             | Résultat local, généré automatiquement (gitignored, jamais commit). Ne jamais éditer directement. |
| `wrangler.jsonc`                 | Config du Worker Cloudflare (nom, dossier `assets`). **Ne pas supprimer** : sans lui, chaque build CI régénère un config à la volée et Cloudflare refuse de redéployer par sécurité (conflit de nom avec le Worker existant, déjà rencontré une fois). |

## Déploiement (Git → Cloudflare, source de vérité)

- **Dépôt** : https://github.com/Draflo/animeandseriestracker (branche `main`).
- **URL publique** : https://animeandseriestracker.flo2533.workers.dev/ — Worker
  Cloudflare avec assets statiques (pas un projet "Pages" classique), rattaché
  au même compte que le tracker Pokémon.
- **Déploiement automatique** : chaque `git push` sur `main` déclenche un build
  Cloudflare qui exécute `python generate.py && mkdir -p dist && cp
  anime-tracker.html dist/index.html`, puis `npx wrangler deploy` (déploie le
  dossier `dist`). Compter ~1-2 min entre le push et la mise à jour de l'URL.
- **Le dossier Google Drive (`Projets/Drive`) n'est plus la source de vérité**
  pour ce projet : ce dépôt Git le remplace. Ne pas éditer les fichiers côté
  Drive en pensant que ça se propage — ça ne se propage pas, ce sont deux
  copies indépendantes désormais.
- Ce dépôt Git n'a pas le risque de troncature Google Drive documenté dans
  generate.py (pas de sync tierce sur le dossier), mais les garde-fous
  d'intégrité du script restent actifs par sécurité (ne font pas de mal).

## Workflow d'édition

1. Cloner/récupérer le dépôt (`git pull`) depuis n'importe quelle machine.
2. Modifier `anime-data.json` selon la demande.
3. Une fois un bloc de modifications terminé (pas après chaque champ modifié
   individuellement), lancer `python generate.py` **en local** pour valider
   les données (genres, statuts, jalons) avant de push — plus rapide que
   d'attendre l'échec du build Cloudflare.
4. `git add`, `git commit`, `git push` sur `main` → déploiement automatique
   (voir section Déploiement ci-dessus).
3. Le script valide les données (genres, statuts, états de jalons) avant de
   générer. S'il remonte une erreur, corriger le JSON puis relancer.

Ne pas relancer `generate.py` après chaque petite modif si plusieurs
changements sont demandés dans la même conversation : le faire une fois à la
fin, quand le bloc de demandes est traité.

### Garde-fou anti-troncature (historique, incident déjà survenu côté Drive)

Cette section décrit un incident survenu quand ce projet vivait dans un
dossier synchronisé Google Drive (`Projets/Drive`), avant la migration vers
ce dépôt Git. Ce dépôt n'a plus ce risque de sync tierce, mais les
garde-fous dans `generate.py` sont restés actifs par sécurité (inoffensifs,
détectent aussi une troncature accidentelle d'un `git pull`/merge foireux).

Le dossier Drive d'origine était synchronisé via Google Drive. Il est arrivé qu'un outil lise
une version périmée/partiellement synchronisée de
`anime-tracker.template.html` (coupée en plein milieu du `<script>`) sans
qu'aucune erreur ne remonte : `generate.py` "réussissait" quand même, en
écrivant un `anime-tracker.html` cassé (squelette visible, mais aucune carte
affichée). C'est déjà arrivé une fois via l'environnement Cowork.

`generate.py` contient maintenant un garde-fou : avant de générer, il vérifie
que le template lu contient bien toute sa structure (balises de fermeture,
fonctions JS clés) ; avant d'écrire le résultat, il vérifie aussi que le HTML
généré est complet (mêmes marqueurs + nombre de séries retrouvées). Si un
souci est détecté, le script s'arrête avec une erreur explicite et
**n'écrase pas** `anime-tracker.html` (écriture atomique via fichier
temporaire) : l'ancienne version valide reste en place.

Si `generate.py` remonte une erreur de ce type :
- Ne pas relancer le script en boucle en espérant que ça passe.
- Relire `anime-tracker.template.html` avec l'outil Read (pas un terminal)
  pour confirmer son contenu réel, attendre que la synchronisation Drive se
  termine, puis relancer.
- Dans Cowork spécifiquement : si le terminal/shell continue de voir une
  version périmée d'un fichier après une édition (ça peut persister plusieurs
  minutes, contrairement aux éditions faites via les outils fichiers qui sont
  fiables immédiatement), ne pas se fier à `python generate.py` lancé depuis
  ce terminal. Reconstruire plutôt `anime-tracker.html` directement avec les
  outils fichiers (lire le template et le JSON avec Read, remplacer
  `{{DATA_JSON}}` par le JSON, écrire le résultat avec Write), puis vérifier
  le fichier obtenu avec Read (débute par `<!DOCTYPE html>`, se termine par
  `</html>`, contient les séries attendues).

## Schéma de `anime-data.json`

### `genres_disponibles`
Liste fixe mais modifiable des genres utilisés (badges sur les cartes).
Actuels : Shonen, Seinen, Horreur, Action, Isekai, Comedie, Drame.
Ne pas ajouter un genre à la volée pour une seule série sans demander : on
garde une liste courte. Si un genre est vraiment nécessaire, l'ajouter ici
avant de l'utiliser.

### `series[]` (anime suivis, en cours ou terminés)
Champs :
- `id` : slug unique.
- `titre`
- `genre` : doit exister dans `genres_disponibles`.
- `statut` : `en_cours` ou `termine`.
- `jalons[]` : liste des éléments à surveiller ou déjà disponibles pour cette
  série (voir logique des couleurs ci-dessous). Tableau vide si rien à
  signaler (typiquement les séries `termine`).
  - `label` : texte court affiché sur le badge (ex: "Saison 3", "Diffusion
    hebdomadaire", "Film Infinity Castle Partie 2").
  - `etat` : `disponible` / `estimation` / `inconnue` (voir plus bas).
  - `date` : optionnel, string libre (ex: "2027"). Affiché uniquement si
    présent, à côté du label.
- `notes` : texte libre. Toujours renseigné si pertinent, mais **affiché
  seulement pour les series classées "en attente de la suite"** (voir plus
  bas). Sert aussi de mémoire pour l'IA même quand non affiché.
- `derniere_maj` : date ISO de dernière modification de cette entrée.
- `coup_de_coeur` : booléen optionnel, utilisable quel que soit le `statut`
  (absent ou `false` = pas coup de cœur). Voir la section dédiée ci-dessous
  pour l'effet sur l'affichage.

### `a_voir[]` (suggestions)
- `titre`, `genre`
- `similaire_a[]` : titres déjà suivis qui justifient la suggestion.
  **Privilégier en priorité les séries `coup_de_coeur: true`** comme
  référence : c'est le signal de goût le plus fort disponible, à utiliser
  avant un titre juste "vu" sans coup de cœur. Une nouvelle suggestion
  justifiée par un coup de cœur est une meilleure suggestion.
- `notes` : affiché sur la carte.

### `pas_interesse[]`
- `titre`, `genre`
- `notes` : pourquoi ça n'a pas plu. Affiché sur la carte (même format que
  les autres, pas un simple tag).

## Logique des couleurs (jalons) — ne pas dévier de ça

Chaque jalon a un `etat` qui pilote sa couleur ET la catégorie d'affichage
de la série :

- **`disponible` (vert)** : soit quelque chose est déjà sorti et pas encore vu
  (un épisode, une saison, un film — ex : diffusion hebdomadaire de One Piece,
  saison déjà diffusée mais pas rattrapée, film déjà sorti), soit une date de
  sortie future est connue **au jour près** (ex : Bleach partie 4, sortie
  confirmée le 25 juillet 2026 → vert même si pas encore sorti).
- **`estimation` (orange)** : une date de sortie future est connue avec une
  précision de **saison ou de mois**, mais rien n'est encore disponible
  (ex : "printemps 2027", "mars 2027").
- **`inconnue` (gris)** : aucune info fiable, ou seulement une année /
  fourchette d'années (ex : "2027", "2027-2028") — trop imprécis pour
  l'orange. Le champ `date` peut quand même être renseigné et affiché même
  en gris (ex : JJK saison 4, "2027").

Résumé de la précision requise par couleur : **rien ou année → gris,
saison/mois → orange, jour exact → vert**.

**Important — couleur vert ≠ classement "En cours"** : un jalon `disponible`
avec une date future au jour près (ex : Bleach, "25 juillet 2026") est vert
*uniquement pour indiquer la précision de l'info*. Tant que cette date n'est
pas passée, la série reste dans **"En attente de la suite"**, pas dans
"En cours". Elle ne bascule en "En cours" que quand la date est effectivement
dépassée (ou pour tout jalon `disponible` sans date, qui lui est réellement
déjà sorti). Le HTML généré gère ça automatiquement (fonction
`estReellementDispo` dans `anime-tracker.template.html`, qui compare la date
du jour au format "JJ mois AAAA" à aujourd'hui) : **ne pas classer une série
manuellement en "En cours" juste parce qu'un jalon est vert avec une date
future**.

Pour que cette comparaison de date fonctionne, toute date au jour près doit
être écrite au format **"JJ mois AAAA"** en toutes lettres (ex : "25 juillet
2026"), jamais en chiffres ou dans un autre format.

**Règle de classement automatique** : une série `en_cours` est affichée dans
la section **"En cours"** si au moins un de ses jalons est réellement
disponible (voir ci-dessus). Sinon elle va dans **"En attente de la suite"**.
Ne pas classer une série manuellement, ça se déduit des jalons.

**Pas de prose de progression** sur les cartes "En cours" (pas de "vu jusqu'à
la saison 2, saison 3 non vue") : le jalon vert suffit, il dit déjà ce qui
est disponible.

**Notes concises pour "En attente de la suite"** : ne pas répéter dans
`notes` ce que le jalon dit déjà (pas de "saison X vue", pas de rappel de ce
qui a été regardé). Le badge + la date suffisent à situer où en est la
série ; les notes ne servent qu'à ajouter du contexte réellement nouveau
(ex : source de l'annonce, précision manquante, spin-off lié).

## Coup de cœur

- `coup_de_coeur: true` sur une série fait apparaître un ♥ rouge, sur la même
  ligne que le badge de genre (juste avant), sur sa carte (pas de texte, pas
  cliquable, juste un repère visuel). Actif dans les sections **En cours**,
  **En attente de la suite** et **Terminé**.
- Pas d'effet d'opacité sur les non-favoris (testé et retiré) : seul le ♥ et
  le tri distinguent les coups de cœur.
- Les coups de cœur sont toujours affichés en premier dans leur grille
  (tri automatique, pas besoin de réordonner `series[]` à la main).
- Ne s'applique pas aux sections Suggestions et Pas intéressé (pas de champ
  `coup_de_coeur` sur `a_voir[]`/`pas_interesse[]`).
- Au-delà de l'affichage, `coup_de_coeur` sert aussi de signal pour la
  génération de suggestions : voir la règle dans `a_voir[]` ci-dessus.

## Affichage (design déjà figé, ne pas re-proposer de variantes sauf demande)

- Thème sombre mais lisible (charbon chaud, pas noir pur). Ne pas repartir sur
  un thème très sombre à faible contraste, ça a été testé et rejeté.
- Sections, toutes repliables avec le même composant, dans cet ordre :
  1. En cours (ouvert par défaut)
  2. Suggestions (ouvert par défaut)
  3. En attente de la suite (ouvert par défaut)
  4. Terminé (fermé par défaut)
  5. Pas intéressé (fermé par défaut)
- Notes affichées uniquement dans : Suggestions, En attente de la suite,
  Pas intéressé. Jamais sur "En cours" ni "Terminé".
- Pas de légende globale des genres dans le HTML (elle vit uniquement dans le
  JSON) : le badge de genre par carte suffit.
- Barre de recherche en haut, filtre en direct par titre/genre sur toutes les
  sections.

## Répartition des outils

- **Claude Code** : édition du JSON + lancement de `generate.py`. C'est
  l'outil par défaut pour toute demande de modif dans ce chat/terminal.
- **Cowork** : réservé pour (1) la recherche périodique automatique des
  dates de sortie manquantes/floues (jalons `estimation`/`inconnue`), pas
  encore mise en place, et (2) les modifs faites depuis un autre appareil
  sans terminal, en travaillant directement sur le dépôt Git
  (`Draflo/animeandseriestracker`) plutôt que sur un dossier synchronisé.
- La source de vérité est ce dépôt Git, pas un dossier synchronisé (voir
  section Déploiement). N'importe quel outil qui peut cloner/éditer/push sur
  `main` peut modifier le tracker ; le déploiement Cloudflare se charge du
  reste automatiquement.

## À faire plus tard (non implémenté)
- Tâche Cowork planifiée (mensuelle) qui scanne les jalons `estimation` et
  `inconnue`, cherche sur le web une date plus précise, et met à jour
  `anime-data.json` en conséquence (puis relance `generate.py`).
