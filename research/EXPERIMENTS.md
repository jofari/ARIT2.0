# EXPERIMENTS.jsonl — registre des tests statistiques (chantier B6)

> **Rien ne se mesure sur ce projet sans avoir ete ecrit ici AVANT.**
> Ouvert le 2026-08-18. Ferme B6, dernier verrou methodologique de `CHANTIERS.md`.

## Pourquoi

Un projet qui teste beaucoup sur les memes 8,5 ans de donnees consomme du credit
statistique a chaque essai. Apres N essais, le meilleur resultat n'est plus une decouverte :
c'est le maximum d'un echantillon de bruit. Deux consequences pratiques :

1. **Sans preenregistrement, on ne peut pas distinguer une hypothese confirmee d'une
   observation post-hoc.** L'hypothese, la metrique de decision et le seuil doivent etre
   figes avant de voir le resultat — sinon la p-value ne veut rien dire.
2. **Sans compteur cumulatif, la correction de tests multiples est impossible.** N doit
   compter TOUS les essais, y compris ceux qu'on n'a jamais rapportes parce qu'ils etaient
   mauvais. C'est le fleau principal, et la seule parade est un compteur qui n'est jamais
   remis a zero.

## Format

Un objet JSON par ligne, append-only. **On ne modifie jamais une ligne existante** : on en
ajoute une nouvelle avec le meme `id` et un `statut` mis a jour, et c'est la derniere qui
fait foi. Champs obligatoires :

| Champ | Role |
|---|---|
| `id` | identifiant stable, cite par le rapport et par le code |
| `date` | date de PREenregistrement (pas de la mesure) |
| `hypothese` | ce qu'on croit, formule de facon falsifiable |
| `substrat` | sur quoi ca tourne, et quelle est son esperance connue |
| `split_autorise` | `train` toujours. `holdout` exige une decision explicite de Jonas |
| `variantes` | figees, nommees, comptees — c'est la taille de la famille de tests |
| `metrique_primaire` | UNE seule, choisie avant |
| `regle_de_decision` | les conditions exactes de chaque issue possible |
| `mde_attendu` | le plus petit effet detectable, calcule AVANT la mesure |
| `issue_attendue` | y compris « indecidable », qui est une issue legitime |
| `deja_connu` | ce qui avait deja ete regarde au moment d'ecrire la ligne (honnetete) |
| `n_essais_cumules` | le compteur, jamais remis a zero |
| `statut` | `preenregistre` -> `mesure` -> `clos` |

## Le compteur

La premiere ligne du registre (`id: dette-retroactive-2026-07-31`) porte la dette deja
consommee avant l'ouverture du registre : **>= 30 essais** sur les memes 8,5 ans, etablis
par `research/pistes_2026-07-31/RAPPORT.md` §1.3. Aucune p-value calculee sur cette periode
n'est interpretable telle quelle. Le compteur part donc de 30, pas de 0.

## Lecture

```powershell
& C:\Users\jofar\venvs\arit\Scripts\python.exe -c "import json,pathlib; [print(f\"{d['statut']:14s} {d['id']:28s} N={d.get('n_essais_cumules','?')}\") for d in map(json.loads, pathlib.Path('research/EXPERIMENTS.jsonl').read_text(encoding='utf-8').splitlines()) if d]"
```
