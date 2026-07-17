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
