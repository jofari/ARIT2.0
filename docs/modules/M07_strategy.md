# M07 — `AritV1.py` (la stratégie freqtrade : le liant, volontairement mince)

**Lien à l'edge** : orchestre le cycle complet entrée→gestion→journal. Zéro logique métier ici — tout est délégué à `arit_lib/` (testable). Si ce fichier dépasse ~250 lignes, c'est que de la logique a fui.

**Libs** : `freqtrade` (IStrategy, informative, stoploss_from_absolute, merge helpers) · `pandas` · `arit_lib.*`.

## Squelette contractuel
```python
class AritV1(IStrategy):
    timeframe = "1h"
    can_short = False
    position_adjustment_enable = True        # requis pour G4 (TP partiel)
    use_custom_stoploss = True
    stoploss = -0.99                          # plancher notionnel ; le vrai SL = custom + exchange
    process_only_new_candles = True

    @informative("4h")
    def populate_indicators_4h(self, df, metadata): ...   # indicateurs 4h AVANT merge
    @informative("1d")
    def populate_indicators_1d(self, df, metadata): ...

    def populate_indicators(self, df, metadata):
        df = features.compute_all(df)                      # colonnes 1h + scores (utilise les *_4h mergées)
        macro = journal.read_macro_state()                 # lecture fichier, jamais réseau
        df = regimes.classify(df, macro)                   # regime, seuil, multiplicateur
        df = cio.conviction(df)                            # conviction, signal_long
        return df

    def populate_entry_trend(self, df, metadata):
        df.loc[df["signal_long"] & df["new_4h"], "enter_long"] = 1
        return df

    def confirm_trade_entry(self, pair, ..., current_time, **kw):
        ok, gate, metrics = risk.gate_check(pair, current_time, self.wallets, Trade, self.config)
        journal.log_gate_check(...)                        # TOUJOURS, succès ou échec
        return ok                                          # inclut la logique véto non-bloquante (11.6)

    def custom_stake_amount(self, pair, ..., **kw):
        return risk.compute_stake(...)                     # + écrit risk_pct/initial_sl/signal_id en custom_data

    def custom_stoploss(self, pair, trade, current_time, current_rate, current_profit, **kw):
        new_abs = gestion.compute_sl(trade, self._closed_1h_row(pair), trade_data(trade))
        return stoploss_from_absolute(new_abs, current_rate) if new_abs else None

    def adjust_trade_position(self, trade, ..., **kw):
        return gestion.partial_tp(trade, ...)              # G4 : stake négatif = vendre 50 %, une fois

    def custom_exit(self, pair, trade, current_time, current_rate, current_profit, **kw):
        return gestion.check_exit(trade, self._closed_1h_row(pair), trade_data(trade))  # "G6"/"G7"/"TP2"/None

    def bot_loop_start(self, current_time, **kw):
        heartbeat.touch(); risk.snapshot_day_equity_if_new_day(...)
```

## Règles propres à ce module
1. `process_only_new_candles = True` + garde `new_4h` : jamais deux évaluations du même setup.
2. `_closed_1h_row(pair)` = dernière bougie 1h **clôturée** (jamais la bougie en cours) — helper unique, testé.
3. Toute exception d'un module `arit_lib` est catchée, journalisée (`system`), et se traduit par l'action la plus sûre : pas d'entrée / pas de modification de SL. Le bot ne crash jamais sur une feature.
4. Aucune constante magique ici : tout vient de `arit_lib/params.py` (un seul fichier de paramètres, miroir exact des valeurs du PDR — source de vérité citée en commentaire, ex. `# PDR 03.4 G3`).
5. Signatures exactes des callbacks : vérifier la doc freqtrade de la version installée au Sprint 0 (les noms ci-dessus sont la référence 2024+ ; les VALEURS et la logique sont contractuelles).
