"""B6 — le registre de preenregistrement, partage par tous les scripts de mesure.

Extrait de `ablation_macro.py` le 2026-08-20 : le verrou servait a une seule experience,
il en garde desormais trois (Q4 ablation des scores, Q11e F&G adaptatif, short/trailing).
Un verrou methodologique duplique est un verrou qu'on finit par contourner.

Le registre `research/EXPERIMENTS.jsonl` est APPEND-ONLY et melange deux natures de lignes :

  - le PROTOCOLE (statut `preenregistre`) : hypothese, hypothese nulle, substrat, variantes,
    metrique, famille de tests, correction, regle de decision, issue attendue. Seule cette
    ligne porte les garde-fous (`split_autorise`, `variantes`).
  - le RESULTAT (`clos`, `mesure`) : ce que la mesure a rendu. Il n'amende jamais un
    protocole ; amender un protocole, c'est ecrire une NOUVELLE ligne `preenregistre`.

Sans hypothese ni regle de decision ecrites AVANT, un resultat post-hoc est indiscernable
d'une hypothese confirmee, et le compteur cumulatif d'essais — seule base honnete d'une
correction de tests multiples — n'existe pas.
"""

import json
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[1]
EXPERIMENTS = REPO / "research" / "EXPERIMENTS.jsonl"

STATUT_PROTOCOLE = "preenregistre"   # ligne qui PORTE le protocole
STATUTS_CLOS = ("clos",)             # experience terminee : rejouer exige un nouvel id


def entrees(chemin: pathlib.Path, id_exp: str) -> list[dict]:
    """Toutes les lignes du registre portant cet id, dans l'ordre du fichier."""
    if not chemin.exists():
        raise SystemExit(f"B6 : registre absent ({chemin}). Preenregistrer avant de mesurer.")
    trouvees = []
    for ligne in chemin.read_text(encoding="utf-8").splitlines():
        if not ligne.strip():
            continue
        try:
            entree = json.loads(ligne)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"B6 : registre illisible ({exc})") from exc
        if entree.get("id") == id_exp:
            trouvees.append(entree)
    return trouvees


def protocole(chemin: pathlib.Path, id_exp: str) -> dict:
    """La ligne de PROTOCOLE en vigueur pour cet id — close ou non. Lecture seule.

    Un amendement de protocole = une nouvelle ligne `preenregistre`, et c'est la derniere
    qui fait foi. Une ligne de resultat n'amende jamais un protocole.
    """
    protocoles = [e for e in entrees(chemin, id_exp) if e.get("statut") == STATUT_PROTOCOLE]
    if not protocoles:
        raise SystemExit(f"B6 : aucun protocole '{id_exp}' (statut '{STATUT_PROTOCOLE}') dans "
                         f"{chemin}. Ecrire l'hypothese, la metrique et la regle de decision "
                         "AVANT de mesurer.")
    return protocoles[-1]


def preenregistrement(chemin: pathlib.Path, id_exp: str) -> dict:
    """B6 — le verrou materialise : pas de protocole, pas de mesure.

    ⚠️ Corrige le 2026-08-20. La regle etait « la DERNIERE ligne de cet id fait foi », ce qui
    renvoyait la ligne de RESULTAT des qu'une experience etait close — une ligne qui ne porte
    ni `split_autorise` ni `variantes`. Le script relance apres cloture tournait donc avec un
    garde-fou VIDE : le verrou cense empecher le p-hacking s'ouvrait precisement apres la
    premiere mesure.

    Deux refus distincts :
      - aucun protocole ecrit  => on ne mesure pas (le verrou d'origine) ;
      - experience DEJA CLOSE  => on ne remesure pas. Rejouer une experience close jusqu'a
        obtenir le bon resultat est la forme la plus directe de p-hacking ; une nouvelle
        mesure exige un nouvel id, donc une ligne de plus au compteur cumulatif d'essais.
    """
    lignes = entrees(chemin, id_exp)
    if not lignes:
        raise SystemExit(f"B6 : aucune entree '{id_exp}' dans {chemin}. "
                         "Ecrire l'hypothese, la metrique et la regle de decision AVANT.")
    if lignes[-1].get("statut") in STATUTS_CLOS:
        raise SystemExit(f"B6 : experience '{id_exp}' CLOSE (statut '{lignes[-1]['statut']}'). "
                         "La remesurer telle quelle est du p-hacking par repetition : "
                         "preenregistrer un NOUVEL id, qui compte comme un essai de plus.")
    return protocole(chemin, id_exp)


def essais_cumules(chemin: pathlib.Path = EXPERIMENTS) -> int:
    """Compteur d'essais CUMULE sur tout le registre (B2 garde 3 : jamais remis a zero).

    Lit la derniere valeur de `n_essais_cumules` ecrite, toutes experiences confondues. Une
    correction de tests multiples appliquee par execution, et non sur la famille cumulee,
    ne corrige rien : elle redemarre le compteur a chaque fois qu'on a envie de mesurer.
    """
    if not chemin.exists():
        return 0
    dernier = 0
    for ligne in chemin.read_text(encoding="utf-8").splitlines():
        if not ligne.strip():
            continue
        valeur = json.loads(ligne).get("n_essais_cumules")
        if isinstance(valeur, int):
            dernier = valeur
    return dernier
