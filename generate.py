#!/usr/bin/env python3
"""
Regenere anime-tracker.html a partir de anime-data.json.

Usage :
    python generate.py

A lancer a chaque fois que anime-data.json a ete modifie
(a la main, par Claude Code, ou par Cowork).
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime

FOLDER = Path(__file__).parent
DATA_FILE = FOLDER / "anime-data.json"
TEMPLATE_FILE = FOLDER / "anime-tracker.template.html"
OUTPUT_FILE = FOLDER / "anime-tracker.html"

REQUIRED_TOP_KEYS = {"genres_disponibles", "genres_series_disponibles", "series", "a_voir", "pas_interesse"}
REQUIRED_SERIES_KEYS = {"id", "titre", "type", "genre", "statut", "jalons", "notes"}
VALID_ETATS = {"disponible", "estimation", "inconnue"}
VALID_STATUTS = {"en_cours", "termine"}
VALID_TYPES = {"anime", "serie"}

# Marqueurs qui doivent obligatoirement etre presents dans un template/HTML
# complet et non tronque. Ce projet est synchronise via Google Drive, et il
# est arrive qu'un outil lise une version en cache/partiellement synchronisee
# du template (coupee en plein milieu du <script>) sans qu'aucune erreur ne
# remonte : le script "reussissait" en ecrivant un HTML casse (squelette
# visible mais aucune carte affichee, JS interrompu avant sa fin). Les
# controles ci-dessous existent pour detecter exactement ce cas de figure.
MARQUEURS_HTML_COMPLET = [
    "{{DATA_JSON}}",
    "function renderTab",
    "function render(",
    "render();",
    "</script>",
    "</body>",
    "</html>",
]


def charger_donnees():
    if not DATA_FILE.exists():
        sys.exit(f"Erreur : {DATA_FILE.name} introuvable dans {FOLDER}")
    try:
        with open(DATA_FILE, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        sys.exit(f"Erreur : {DATA_FILE.name} contient du JSON invalide -> {e}")
    return data


def valider(data):
    erreurs = []

    missing = REQUIRED_TOP_KEYS - data.keys()
    if missing:
        erreurs.append(f"Cles manquantes a la racine : {sorted(missing)}")

    genres_par_type = {
        "anime": set(data.get("genres_disponibles", [])),
        "serie": set(data.get("genres_series_disponibles", [])),
    }

    def verifier_genre(label, type_, genre, erreurs):
        genres_connus = genres_par_type.get(type_)
        if genres_connus is None:
            return
        liste = "genres_disponibles" if type_ == "anime" else "genres_series_disponibles"
        if genre not in genres_connus:
            erreurs.append(f"[{label}] genre '{genre}' absent de {liste}")

    for i, s in enumerate(data.get("series", [])):
        label = s.get("titre", f"entree #{i}")
        missing = REQUIRED_SERIES_KEYS - s.keys()
        if missing:
            erreurs.append(f"[{label}] champs manquants : {sorted(missing)}")
            continue
        if s["statut"] not in VALID_STATUTS:
            erreurs.append(f"[{label}] statut invalide : {s['statut']}")
        if s["type"] not in VALID_TYPES:
            erreurs.append(f"[{label}] type invalide : {s['type']}")
        else:
            verifier_genre(label, s["type"], s["genre"], erreurs)
        for j in s.get("jalons", []):
            if j.get("etat") not in VALID_ETATS:
                erreurs.append(f"[{label}] etat de jalon invalide : {j.get('etat')}")
        if "coup_de_coeur" in s and not isinstance(s["coup_de_coeur"], bool):
            erreurs.append(f"[{label}] coup_de_coeur doit etre un booleen (true/false)")

    for i, s in enumerate(data.get("a_voir", [])):
        label = s.get("titre", f"suggestion #{i}")
        type_ = s.get("type")
        if type_ not in VALID_TYPES:
            erreurs.append(f"[{label}] type invalide : {type_}")
        else:
            verifier_genre(label, type_, s.get("genre"), erreurs)

    for i, s in enumerate(data.get("pas_interesse", [])):
        label = s.get("titre", f"entree #{i}")
        type_ = s.get("type")
        if type_ not in VALID_TYPES:
            erreurs.append(f"[{label}] type invalide : {type_}")
        else:
            verifier_genre(label, type_, s.get("genre"), erreurs)

    return erreurs


def verifier_integrite(contenu, nom_fichier, exiger_placeholder):
    """Verifie qu'un contenu HTML (template ou sortie) n'est pas tronque.
    Retourne une liste de problemes (vide si tout va bien)."""
    problemes = []
    for marqueur in MARQUEURS_HTML_COMPLET:
        if marqueur == "{{DATA_JSON}}" and not exiger_placeholder:
            continue
        if marqueur not in contenu:
            problemes.append(f"marqueur manquant : {marqueur!r}")
    if not contenu.rstrip().endswith("</html>"):
        problemes.append("le fichier ne se termine pas par </html> (troncature probable)")
    if problemes:
        problemes.insert(0, f"{nom_fichier} semble tronque/incomplet :")
    return problemes


def generer():
    data = charger_donnees()

    erreurs = valider(data)
    if erreurs:
        print("Le fichier de donnees contient des problemes :\n")
        for e in erreurs:
            print(f"  - {e}")
        print("\nCorrige anime-data.json puis relance le script.")
        sys.exit(1)

    if not TEMPLATE_FILE.exists():
        sys.exit(f"Erreur : {TEMPLATE_FILE.name} introuvable dans {FOLDER}")

    template = TEMPLATE_FILE.read_text(encoding="utf-8")

    # Le dossier est synchronise via Google Drive : si un outil lit ce fichier
    # au mauvais moment (sync en cours), il peut recevoir une version tronquee
    # sans qu'aucune erreur de lecture ne se produise. On verifie donc que le
    # template a bien toute sa structure avant de s'en servir.
    problemes_template = verifier_integrite(template, TEMPLATE_FILE.name, exiger_placeholder=True)
    if problemes_template:
        print("Erreur : le template lu est incomplet (probable souci de synchronisation) :\n")
        for p in problemes_template:
            print(f"  - {p}")
        print(
            f"\nRelis {TEMPLATE_FILE.name} (par exemple avec l'outil Read) pour confirmer son contenu reel, "
            "attends que la synchronisation se termine, puis relance le script. "
            "Ne relance pas generate.py en boucle si le probleme persiste : ca produirait a nouveau un HTML casse."
        )
        sys.exit(1)

    html = template.replace("{{DATA_JSON}}", json.dumps(data, ensure_ascii=False, indent=2))

    # Verification de la sortie AVANT de toucher au vrai fichier : on ecrit
    # dans un fichier temporaire, on verifie son integrite, et on ne remplace
    # anime-tracker.html que si tout est bon (ecriture atomique). Comme ca,
    # si un probleme est detecte, l'ancien anime-tracker.html (valide) reste
    # en place au lieu d'etre ecrase par une version cassee.
    problemes_sortie = verifier_integrite(html, OUTPUT_FILE.name, exiger_placeholder=False)
    n_series = len(data["series"])
    n_id_trouves = html.count('"id":')
    if n_id_trouves < n_series:
        problemes_sortie.append(
            f"seulement {n_id_trouves}/{n_series} series retrouvees dans le HTML genere (troncature probable)"
        )
    if problemes_sortie:
        print("Erreur : le HTML genere semble incomplet, generation annulee (l'ancien fichier n'a pas ete touche) :\n")
        for p in problemes_sortie:
            print(f"  - {p}")
        sys.exit(1)

    tmp_file = OUTPUT_FILE.with_suffix(".tmp")
    tmp_file.write_text(html, encoding="utf-8")
    os.replace(tmp_file, OUTPUT_FILE)  # remplacement atomique

    n_a_voir = len(data["a_voir"])
    n_pas_interesse = len(data["pas_interesse"])
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    print(f"[{now}] {OUTPUT_FILE.name} regenere avec succes")
    print(f"  series suivies : {n_series}  |  suggestions : {n_a_voir}  |  pas interesse : {n_pas_interesse}")


if __name__ == "__main__":
    generer()
