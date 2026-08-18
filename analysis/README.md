# analysis/ — outillage d'analyse hors-ligne (E0)

Outils d'analyse PURS (aucun code produit, aucun import freqtrade) qui exploitent les
artefacts existants : zips de backtest, journal `logs/decisions/`, feathers OHLCV.
Sorties dans `analysis/out/` (gitignoré).

## replay_entries.py — atlas des excursions (déployé 2026-07-17, décision Jonas)

Rejoue chaque entrée d'un run de backtest sur l'OHLCV brut (5m par défaut), avec pour
seule règle le **SL initial structurel** (docs/03 §3.3, retrouvé dans les événements
`entry` du journal) et un horizon (90 j). Produit par entrée : outcome (TP +1,5R avant
SL / SL / open), premières touches en R, MFE/MAE (brut fenêtre ET capturable avant SL),
continuation capturable après +1,5R, giveback pic→creux, marques hold 7/30/90 j, et la
trajectoire 1h complète (`trajectories_1h.parquet`).

```powershell
& C:\Users\jofar\venvs\arit\Scripts\python.exe analysis\replay_entries.py `
  --zip backtest_lanes\run2\backtest_results\backtest-result-2026-07-11_15-09-24.zip
```

Validation (run A du protocole, 2026-07-17) : 55/55 SL retrouvés au journal · cohérence
`tp1 == entry + 1,5×(entry−SL)` à 0,0000 % · sur les 17 gagnants zip nets exploitables,
la 1re touche +1,5R du replay précède la clôture zip de 0,4-1,0 h dans 100 % des cas
(sortie sur clôture 1h suivante — sémantique contrôle A reproduite).

**Limites assumées** : R-space par trade — ne simule ni sizing, ni slots, ni compounding,
ni frais ; l'ensemble d'entrées analysé est celui que le run source a réellement pris
(biais de saturation des slots — voir BUILD_NOTES 2026-07-17). Le verdict portefeuille
exige un re-run freqtrade après correction du contrôle A.

## ablation_macro.py — A5, la porte macro mesurée par filtrage (2026-08-18)

Recalcule le signal à partir des colonnes du dataset G0 (`conviction`, `seuil`, `rr_dispo`,
`regime`, `trend_dir`) et ne fait varier **que** la porte macro, sur quatre variantes gelées
d'avance : production · sans la pénalité NEUTRE (l'alternative écartée par A5) · PORTEUR et
HOSTILE seuls · porte désactivée (contrôle négatif). Aucun code de production n'est touché ;
la variante « production » doit reproduire exactement `signal_long`/`signal_short` du dataset,
sinon le script s'arrête.

```powershell
& C:\Users\jofar\venvs\arit\Scripts\python.exe analysis\ablation_macro.py `
    --json analysis\out\ablation_A5.json
```

**Trois garde-fous, tous matériels :**
- **B6** — refuse de tourner si l'expérience n'est pas préenregistrée dans
  `research/EXPERIMENTS.jsonl` (hypothèse, métrique, règle de décision, MDE attendu) ;
- **B5** — ne lit que `split='train'` et vérifie qu'aucune ligne de hold-out n'a survécu ;
- **emboîtement** — V2 ⊂ V0 ⊂ V1 ⊂ V3 vérifié à l'exécution, sans quoi les « signaux
  marginaux » n'ont pas de sens.

**Ce qui est mesuré** : l'espérance en R des signaux **marginaux** (ceux qu'une porte bloque),
comparée à celle du noyau qu'elle laisse passer. Jamais le résultat total : le substrat a une
espérance négative (−0,0123 R long, −0,0370 R short), donc tout filtre qui bloque des trades
améliore le total **sans rien trier**. Statistique : binomial exact contre le modèle nul B1,
Benjamini-Hochberg (FDR 0,10) sur la famille déclarée, IC par bootstrap par blocs
stationnaire (ℓ fixé avant, sensibilité publiée sur 1/3/6), MDE affiché **avant** toute
p-value.

Verdict du run du 18/08 : **indécidable** — 7 signaux marginaux en 5 ans pour un MDE de
+1,53 R. Rapport : `research/ablation_A5/RAPPORT.md`.
