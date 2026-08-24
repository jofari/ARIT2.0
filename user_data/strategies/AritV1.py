"""M07 - AritV1 : strategie freqtrade mince (docs/modules/M07), zero logique metier (delegue a
arit_lib/, pur+teste). Aucun reseau dans les callbacks (docs/11 par.11.5) ; exception arit_lib ->
action sure + journal 'system' ; noms/constantes = arit_lib.contracts/params (zero magie)."""

import math
from pathlib import Path

import pandas as pd
from freqtrade.persistence import Trade
from freqtrade.strategy import informative, stoploss_from_absolute

try:  # IStrategy tire scipy (rpc/metrics), indispo dans le venv de test pur.
    from freqtrade.strategy import IStrategy
except Exception:  # pragma: no cover - fallback tests (helpers purs restent importables)
    IStrategy = object

from arit_lib import cio, contracts, features, gestion, journal, macro_regime, params, regimes, risk

_LIVE_MODES = ("live", "dry_run")  # live/dry : macro_state.json ; backtest : colonne macro (M08)
_safe = journal.safe               # M07 regle 3 : exception callback -> 'system' + action sure


def _num(value) -> float:
    return float(value) if value is not None and pd.notna(value) else float("nan")


class AritV1(IStrategy):
    timeframe = params.TIMEFRAME_BASE
    can_short = True                             # A2 (Jonas 03/08) : long ET short
    # Levier : on garde le defaut freqtrade (1.0, cf. IStrategy.leverage) => exposition
    # identique au spot, le short ne l'augmente pas. Le choix d'un levier > 1 est une
    # DECISION DE RISQUE non signee — voir DECISIONS.md, question ouverte A2-ter.
    position_adjustment_enable = True            # requis G4 (PDR 03.4)
    use_custom_stoploss = True
    stoploss = -0.99                             # plancher ; vrai SL = custom + exchange
    process_only_new_candles = True              # docs/11 par.11.2
    startup_candle_count = params.STARTUP_CANDLES  # warm-up EMA200 1d (A1 03/08, cf. params)
    protections = params.PROTECTIONS              # C6 07.1 ; backtest : --enable-protections
    def __init__(self, config=None):
        super().__init__(config)
        self._pending: dict = {}
    def _log(self, event, *args) -> None:  # event -> journal.ev_<event> (docs/08.1)
        journal.write(event, getattr(journal, "ev_" + event)(*args))
    @informative(params.TIMEFRAME_SETUP)
    def populate_indicators_4h(self, df, metadata):
        df = features.add_indicators(df)
        df = features.find_pivots(df)
        df = features.track_structure(df)
        return features.candle_patterns(features.sr_levels(df))
    @informative(params.TIMEFRAME_CONTEXT)
    def populate_indicators_1d(self, df, metadata):
        return features.add_indicators(df)
    def populate_indicators(self, df, metadata):
        try:
            df = features.compute_all(df)                    # colonnes 1h + scores (utilise *_4h)
            macro = journal.read_macro_state()               # fichier, jamais reseau
            live = self.dp.runmode.value in _LIVE_MODES      # live/dry vs backtest
            df = (macro_regime.attach_regime_now(df, macro) if live      # A2 : parite live
                  else regimes.attach_macro_regime(df, self._macro_daily()))   # backtest
            df = cio.conviction(regimes.classify(df, macro if live else None))
            self._journal_evaluation(df, metadata.get("pair"), macro, live)
        except Exception as exc:                             # une feature ne crashe jamais le bot
            journal.write("system", journal.ev_system("indicators_error", {"error": str(exc)}))
        return df
    def populate_entry_trend(self, df, metadata):
        df["enter_long"] = 0
        df["enter_short"] = 0                    # A2 : colonne toujours posee (freqtrade 2026.6)
        if "new_4h" not in df.columns:
            return df
        # Garde new_4h (docs/11 par.11.2) : jamais deux evaluations du meme setup 4h.
        new4 = df["new_4h"].fillna(False)
        for col, signal in (("enter_long", "signal_long"), ("enter_short", "signal_short")):
            if signal in df.columns:
                df.loc[df[signal].fillna(False) & new4, col] = 1
        return df
    def populate_exit_trend(self, df, metadata):
        return df  # sorties par callbacks (G6/G7/TP2) ; stub requis au chargement freqtrade 2026.6
    @_safe(False, "gate_error")
    def confirm_trade_entry(self, pair, current_time, **kwargs):
        row = self._closed_1h_row(pair)
        if row is None:
            return False
        trades = Trade.get_trades_proxy()
        udd = Path(self.config.get("user_data_dir", "user_data"))
        sid = self._signal_id(pair, row)
        cooldown, _ = risk.cb_sequential_state(trades, current_time)         # CB sequentiel 03.5
        if cooldown or risk.cb_day_active(self.wallets, current_time, udd):   # CB jour 03.5
            self._log("system", "circuit_breaker", {"pair": pair, "sid": sid})
            return False
        veto = (params.VETO_WINDOW_MIN_DRYRUN if self.config.get("dry_run", True)
                else params.VETO_WINDOW_MIN_CANARI)                          # PDR 11.6
        short = kwargs.get("side") == contracts.DIR_SHORT   # A2 : sens fourni par freqtrade
        rr_col = "rr_dispo_short" if short else "rr_dispo"  # A2 : la porte RR lit le SENS vise
        cfg = {"regime": row.get("regime"), "spread_frac": None,   # spread gate : cf. ecart
               "rr": _num(row.get(rr_col)), "signal_id": sid, "user_data_dir": udd,
               "risk_pct": self._entry_risk_pct(row, trades, current_time), "veto_window_min": veto}
        ok, gate, metrics = risk.gate_check(pair, current_time, self.wallets, trades, cfg)
        self._log("gate_check", sid, [metrics], "enter" if ok else "skip", gate, pair)  # n6
        return bool(ok)
    @_safe(0.0, "stake_error")
    def custom_stake_amount(self, pair, current_time, current_rate, min_stake, **kwargs):
        row = self._closed_1h_row(pair)
        if row is None:
            return 0.0
        trades = Trade.get_trades_proxy()
        sign = contracts.direction_sign(kwargs.get("side") == contracts.DIR_SHORT)  # A2
        sl0, tp1, tp2 = gestion.entry_levels(row, current_rate, sign)         # PDR 03.3 (A2)
        sid = self._signal_id(pair, row)
        if not math.isfinite(sl0):
            self._log("gate_check", sid, [], "skip", contracts.SKIP_ZERO_STOP_DISTANCE, pair)
            return 0.0
        risk_pct = self._entry_risk_pct(row, trades, current_time)
        equity = float(self.wallets.get_total_stake_amount())    # equite courante (compounding)
        stake, reason = risk.compute_stake(                  # tuple (stake|None, raison)
            equity, risk_pct, current_rate, sl0, min_notional=min_stake or 0.0, sign=sign)
        if stake is None:                                    # skip journalise avec raison (n6)
            self._log("gate_check", sid, [], "skip", reason, pair)
            return 0.0
        # Q14 : freqtrade clampe le stake a max_stake EN SILENCE => risque reel < risk_pct.
        cap = risk.plafonnement_stake(stake, kwargs.get("max_stake"), equity, current_rate,
                                      sl0, risk_pct, sign)
        if cap is not None:
            self._log("system", contracts.STAKE_CAP_KIND, dict(cap, pair=pair, signal_id=sid))
        conv = "conviction" if sign > 0 else "conviction_short"
        self._pending[pair] = {
            "initial_sl": sl0, "risk_pct": risk_pct, "signal_id": sid, "tp1": tp1, "tp2": tp2,
            "entry_conviction": _num(row.get(conv)), "entry_regime": row.get("regime"),
            "is_short": sign < 0, "trade_no": risk.trade_counter(trades) + 1}
        return float(stake)
    @_safe(None, "order_filled_error")
    def order_filled(self, pair, trade, order, **kwargs):
        if not trade.is_open:                                # fill de sortie -> journal exit
            return self._journal_exit(trade)
        entry_side = "sell" if getattr(trade, "is_short", False) else "buy"  # A2 : short = SELL
        if getattr(order, "ft_order_side", entry_side) != entry_side:  # sortie G4 : deja loggee
            return None
        if trade.get_custom_data("initial_sl") is not None or pair not in self._pending:
            return None
        p = self._pending.pop(pair)
        state = contracts.TradeState(
            initial_sl=p["initial_sl"], risk_pct=p["risk_pct"], trade_no=p["trade_no"],
            entry_conviction=p["entry_conviction"], entry_regime=p["entry_regime"],
            signal_id=p["signal_id"], tp2=p["tp2"] or 0.0,    # TP2 fige a l'entree (11.3, PDR 03.3)
            is_short=bool(getattr(trade, "is_short", p["is_short"])))  # A2 : sens fige a l'entree
        self._save_state(trade, state)
        tinfo = {"pair": trade.pair, "open_rate": trade.open_rate, "amount": trade.amount,
                 "stake_amount": trade.stake_amount, "open_date": trade.open_date_utc,
                 "tp1": p["tp1"], "tp2": p["tp2"], "signal_id": p["signal_id"]}
        self._log("entry", tinfo, state)
        return None
    @_safe(None, "stoploss_error")
    def custom_stoploss(self, pair, trade, current_rate, after_fill, **kwargs):
        row = self._closed_1h_row(pair)
        state = self._trade_state(trade)
        # Floor = SL initial structurel, offert a CHAQUE appel — PAS seulement after_fill :
        # l'appel after_fill precede l'ecriture du custom_data par order_filled, donc un floor
        # conditionne a after_fill n'est JAMAIS pose (bug campagne A/B — controle A sans stop
        # 8,5 ans, BUILD_NOTES 2026-07-17). Idempotent : freqtrade ne bouge le SL que vers le
        # haut, le floor est ignore des qu'un G-rule l'a depasse. initial_sl == 0 (custom_data
        # pas encore ecrit) => None, jamais un floor a ~0.
        # A1 (24/08) : `is_short` OBLIGATOIRE — sans lui un stop de short (au-DESSUS du prix)
        # rend 0.0, que freqtrade jette (0.0 est falsy) : aucun short n'avait de stop.
        short = state.sign < 0
        floor = None
        if state.initial_sl:
            floor = stoploss_from_absolute(state.initial_sl, current_rate, is_short=short)
        if row is None:
            return floor
        gestion.update_excursions(state, row, trade.open_rate)
        new_abs = gestion.compute_sl(trade, row, state)      # max(G1/G2/G3), jamais elargi
        self._save_state(trade, state)
        if new_abs is not None:
            r = gestion.r_multiple(current_rate, trade.open_rate, state.initial_sl, state.sign)
            self._log("gestion", {"pair": trade.pair, "signal_id": state.signal_id},
                      "SL", trade.stop_loss, new_abs, r)
            return stoploss_from_absolute(new_abs, current_rate, is_short=short)
        return floor
    @_safe(None, "adjust_error")
    def adjust_trade_position(self, trade, **kwargs):
        row = self._closed_1h_row(trade.pair)
        if row is None:
            return None
        state = self._trade_state(trade)
        gestion.update_excursions(state, row, trade.open_rate)
        stake = gestion.partial_tp(trade, state.mfe_r, state)    # G4 : premier touch +1,5R
        if state.tp1_done and not state.extension_on and bool(row.get("bos_fresh_4h")):
            state.extension_on = True                           # G5 (M05 par.2.5)
        self._save_state(trade, state)
        if stake is not None:
            self._log("gestion", {"pair": trade.pair, "signal_id": state.signal_id},
                      "G4", trade.amount, stake, state.mfe_r)
        return stake
    @_safe(None, "exit_error")
    def custom_exit(self, pair, trade, **kwargs):
        row = self._closed_1h_row(pair)
        if row is None:
            return None
        state = self._trade_state(trade)
        gestion.update_excursions(state, row, trade.open_rate)
        # TP2 de SORTIE = niveau 4h COURANT recalcule chaque cloture 1h (decision Jonas
        # 2026-07-09, docs/03 par.3.3 amendement) ; state.tp2 reste en custom_data pour l'audit.
        # A2 : resistance pour un long, SUPPORT pour un short.
        level = _num(row.get("nearest_res_4h" if state.sign > 0 else "nearest_sup_4h"))
        tp2 = level if math.isfinite(level) else None
        reason = gestion.check_exit(trade, row, state, tp2)     # "G6"/"G7"/"TP2"/None
        self._save_state(trade, state)
        return reason

    @_safe(None, "loop_error")
    def bot_loop_start(self, current_time, **kwargs):
        udd = Path(self.config.get("user_data_dir", "user_data"))
        hb = udd / contracts.HEARTBEAT_FILE
        hb.parent.mkdir(parents=True, exist_ok=True)
        hb.touch()
        risk.snapshot_day_equity_if_new_day(self.wallets, current_time, udd)  # ref CB -6 %
    # --- helpers purs (etat trade, sizing, niveaux 03.3, journal derive) ---
    def _closed_1h_row(self, pair):  # derniere bougie 1h CLOTUREE, jamais la courante (M07 regle 2)
        df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        return df.iloc[-1] if df is not None and len(df) else None
    def _macro_daily(self):  # regimes macro quotidiens point-in-time (backtest) : charge+cache 1x
        if not hasattr(self, "_macro_cache"):
            d = Path(self.config.get("user_data_dir", "user_data")) / contracts.MACRO_DATA_DIR
            self._macro_cache, events = macro_regime.daily_with_equity_veto(d)
            for kind, detail in events:                 # macro_unavailable / equity_veto_stale
                journal.write("system", journal.ev_system(kind, detail))
        return self._macro_cache
    def _trade_state(self, trade):
        data = {k: trade.get_custom_data(k) for k in contracts.CUSTOM_DATA_KEYS}
        return contracts.TradeState.from_dict({k: v for k, v in data.items() if v is not None})
    def _save_state(self, trade, state) -> None:
        for key, value in state.as_dict().items():     # cles 11.3 exclusivement
            trade.set_custom_data(key, value)
    def _entry_risk_pct(self, row, trades, now) -> float:
        _, divisor = risk.cb_sequential_state(trades, now)      # /2 pendant penalite (PDR 03.5)
        return risk.compute_risk_pct(_num(row.get("conviction")), _num(row.get("seuil")),
                                     risk.trade_counter(trades) + 1, divisor)
    def _signal_id(self, pair, row) -> str:
        ts = row.get("date_4h")
        if ts is None or pd.isna(ts):
            ts = row.get("date")
        return contracts.make_signal_id(pair, pd.Timestamp(ts).to_pydatetime())
    def _journal_evaluation(self, df, pair, macro, live) -> None:
        # 'evaluation' /cloture 4h (11.1) ; scope elargi au BACKTEST le 12/08 (journal.py).
        if pair is None:
            return
        for row in journal.lignes_evaluation(df, live):
            # A2 : un no_signal ne doit pas masquer un signal short. La raison porte le SENS
            # signale, c'est ce qui rend le Test 1 de docs/01 lisible dans le journal.
            sig = [d for d, col in ((contracts.DIR_LONG, "signal_long"),
                                    (contracts.DIR_SHORT, "signal_short")) if bool(row.get(col))]
            # macro_state.json porte l'etat COURANT : l'ecrire sur une bougie de 2021 serait du
            # look-ahead. Le contexte macro point-in-time est deja dans la row en backtest.
            exp = {"pair": pair, "signal_id": self._signal_id(pair, row),
                   "decision": "signal" if sig else "no_signal",
                   "raison": "/".join(sig) if sig else row.get("regime"),
                   "close_vs_ema": cio.explain(row)["regime_inputs"]["close_vs_ema"],
                   "fear_greed": macro.get("fear_greed") if live else None,
                   "macro_stale": macro.get("stale") if live else None}
            self._log("evaluation", row, exp)
    def _journal_exit(self, trade) -> None:
        state = self._trade_state(trade)
        r = (gestion.r_multiple(trade.close_rate, trade.open_rate, state.initial_sl, state.sign)
             if state.initial_sl else 0.0)
        info = {"pair": trade.pair, "signal_id": state.signal_id,
                "open_date": trade.open_date_utc, "close_date": trade.close_date_utc}
        fees = getattr(trade, "fee_close", params.FEE_TAKER_FRAC)
        self._log("exit", info, getattr(trade, "exit_reason", None), r, state.mae_r, state.mfe_r,
                  fees, params.SLIPPAGE_FRAC.get(contracts.spot_pair(trade.pair)))  # cle sans ':'
