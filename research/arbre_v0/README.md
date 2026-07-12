# arbre_v0 — POC event study FOMC/CPI → BTC

Test de faisabilité : les événements macro calendaires (FOMC, CPI US) prédisent-ils la direction du BTC
à J+1/J+7 ? Event study bayésien (Beta(2,2), bootstrap, Brier walk-forward). Verdict : voir `RESULTATS.md`.

Relancer : `python fetch_dates.py` (régénère `data/*.csv` depuis federalreserve.gov + Wayback/BLS, cache
HTML dans `data/raw_html/` → marche hors-ligne si le cache existe), puis `python event_study.py`
(seed=42, lit `user_data/data/binance/BTC_USDT-1d.feather` relatif à la racine du repo, tables sur stdout).
