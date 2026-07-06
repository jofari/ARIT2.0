# 02 — Architecture v3 (freqtrade-first)

## Vue d'ensemble (mermaid)
```mermaid
flowchart TD
    BIN([Binance spot WS/REST]):::api
    FIN([Finnhub calendrier eco]):::api
    FG([alternative.me Fear&Greed]):::api
    DISC([Discord webhook + bot]):::api

    subgraph FT["FREQTRADE - fourni, ne pas recoder"]
        DATA[Data 1h/4h/1d + detail 5m]:::blue
        EXEC[Execution + reconciliation]:::blue
        PROT[Protections CB jour + sequentiel]:::blue
        DB[(SQLite trades)]:::blue
        UI[FreqUI local read-only]:::blue
        BT[Backtest + hyperopt]:::blue
    end

    subgraph STRAT["STRATEGIE AritV1 - a coder"]
        FEAT[features.py<br/>structure BOS/CHoCH · S/R · indicateurs · patterns CDL · volume]:::red
        REG[regimes.py<br/>TREND / TRANSITION / RANGE / RISK_OFF]:::red
        CIO[cio.py<br/>profil de poids par regime · multiplicateur · conviction]:::red
        ENTRY[entry logic<br/>seuil par regime + RR>=1.5]:::red
        VETO[confirm_trade_entry<br/>news · liquidite · budgets hebdo · residuel 6pct · veto canari]:::red
        SIZE[custom_stake_amount<br/>mapping conviction -> risque]:::red
        GEST[G1-G7<br/>custom_stoploss + adjust_trade_position + custom_exit]:::red
        JRNL[journal.py<br/>JSONL chaque decision + digest]:::red
    end

    subgraph SVC["SERVICES LOCAUX - a coder"]
        MACRO[macro_state.py<br/>horaire -> JSON]:::red
        DBOT[discord_bot.py<br/>notifs + veto canari]:::red
        WD[watchdog.py<br/>heartbeat + flatten urgence]:::red
    end

    subgraph V2["V2 - NE PAS CODER MAINTENANT"]
        FAI[FreqAI meta-modele]:::green
        HMM[HMM regimes appris]:::green
        MAE[Modele MAE/MFE]:::green
    end

    BIN --> DATA --> FEAT --> REG --> CIO --> ENTRY --> VETO --> SIZE --> EXEC
    FIN --> MACRO --> VETO
    FG --> MACRO
    EXEC --> GEST --> EXEC
    GEST --> JRNL
    VETO --> JRNL
    EXEC --> DB
    JRNL --> DISC
    DBOT <--> DISC
    DBOT -. veto canari .-> VETO
    WD -. urgence .-> BIN
    DB -. dataset futur .-> FAI
    JRNL -. dataset futur .-> FAI

    classDef red fill:#fde2e2,stroke:#c0392b,color:#7b1e1e;
    classDef green fill:#dff5e1,stroke:#27ae60,color:#145a32;
    classDef blue fill:#dbeafe,stroke:#2563eb,color:#1e3a5f;
    classDef api fill:#ece3f5,stroke:#8e44ad,color:#512e5f;
```
Légende : **rouge** = à coder (V1) · **bleu** = fourni par freqtrade (interdiction de le recoder) · **vert** = V2, ne pas toucher · **violet** = API externe.

## Flux d'une décision (précis)
1. Clôture d'une bougie 4h → `populate_indicators` a déjà calculé toutes les features (1h base + colonnes 4h/1d mergées sans look-ahead).
2. `regimes.py` classe le contexte → régime + profil de poids + seuil + multiplicateur.
3. `cio.py` calcule les scores de modules (05), applique le profil → conviction.
4. Signal d'entrée si conviction ≥ seuil du régime ET RR dispo ≥ 1,5.
5. `confirm_trade_entry` : vetos (news, liquidité), budgets (hebdo 8 %, 10 entrées, résiduel ≤ 6 %, slots ≤ 3), véto Discord si phase canari. Chaque évaluation → ligne de journal (entrée OU skip motivé).
6. `custom_stake_amount` : conviction → risque % → taille (équité courante).
7. Position ouverte → G1-G7 à chaque clôture 1h (callbacks). Chaque action de gestion → journal.
8. Sortie → journal complet (cause, R, MAE/MFE) → SQLite + Discord.

## Layout du repo
```
arit/
├── user_data/
│   ├── strategies/
│   │   ├── AritV1.py            # la stratégie freqtrade (orchestration fine)
│   │   └── arit_lib/            # logique métier importée (testable en pytest)
│   │       ├── features.py      # 05
│   │       ├── regimes.py       # 04
│   │       ├── cio.py           # 04
│   │       ├── risk.py          # 03 (sizing, budgets, résiduel)
│   │       ├── gestion.py       # 03 (G1-G7)
│   │       └── journal.py       # 08
│   ├── config.dry.json          # 07
│   └── logs/decisions/          # JSONL par jour
├── services/
│   ├── macro_state.py           # 06
│   ├── discord_bot.py           # 08
│   └── watchdog.py              # 09
├── docs/                        # CE dossier PDR v3
└── tests/                       # pytest sur arit_lib (features, risk, regimes)
```
Règle : `AritV1.py` reste mince (callbacks freqtrade) ; toute la logique vit dans `arit_lib/` en fonctions pures testables (entrées = DataFrames/valeurs, sorties = valeurs). Pandas autorisé partout pour la manipulation de données ; règles métier explicites et lisibles par-dessus.

## Ce que freqtrade fournit (NE PAS recoder)
Données et websockets · exécution/reconciliation/fills partiels · dry-run wallet · Protections · SQLite des trades · FreqUI · backtesting/hyperopt · intégration Discord (webhook). Toute tentation de réécrire une de ces briques = STOP, demander à Jonas.
