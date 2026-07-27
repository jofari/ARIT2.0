"""RECHERCHE — MacroFlip : le Macro Analyst V1.1 SEUL, sans technique ni gestion.

Experience demandee par Jonas (2026-07-27) : isoler la couche macro (docs/06 par.6.2) et
mesurer ce qu'elle vaut nue, apres le verdict « edge d'entree NUL » de la campagne A/B
corrigee (BUILD_NOTES 2026-07-19). Regle unique, aucune autre condition :

    PORTEUR (bull)  -> LONG        HOSTILE (bear) -> SHORT (le « put » de Jonas)
    NEUTRE          -> on GARDE la position en cours (aucun ordre)

Ni SL ni TP : on ne sort que sur signal macro inverse, et on reinvestit dans l'autre sens
sur la meme bougie. 50 % de l'equite a chaque entree (compounding), levier 1x.

CE FICHIER N'EST PAS DU CODE DE PRODUCTION : AritV1 (M07) et son contrat sont intouches.
Aucune G-rule, aucun gate de risque, aucun journal — c'est un banc de mesure, pas un bot.
Le regime macro vient du module PUR `arit_lib.macro_regime` (point-in-time : la ligne du
jour J ne reflete que des donnees <= J-1) attache par `regimes.attach_macro_regime`
(merge_asof backward, unites datetime normalisees — piege du 2026-07-13). Zero look-ahead.
"""

import os
from pathlib import Path

from freqtrade.strategy import IStrategy

from arit_lib import contracts, macro_regime, params, regimes

_PORTEUR, _NEUTRE, _HOSTILE = params.MACRO_REGIMES

# Variante secondaire (ARIT_MACRO_FLAT_NEUTRE=1) : NEUTRE remet a plat au lieu de garder la
# position. Defaut = 0 = la regle telle que Jonas l'a formulee (on n'agit QUE sur bull/bear).
FLAT_ON_NEUTRE = os.environ.get("ARIT_MACRO_FLAT_NEUTRE", "") == "1"

# « 50 % a chaque fois » (demande Jonas) : fraction de l'equite TOTALE engagee par entree.
STAKE_FRACTION = 0.5


class MacroFlip(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = params.TIMEFRAME_SETUP          # 4h (demande Jonas)
    can_short = True                            # short perp = le « put »
    minimal_roi = {"0": 10000}                  # aucun TP (10 000 = jamais atteint)
    stoploss = -0.99                            # aucun SL : plancher inerte, pas de callback
    use_custom_stoploss = False
    trailing_stop = False
    use_exit_signal = True                      # les sorties sont le signal macro inverse
    exit_profit_only = False                    # on sort aussi en perte : c'est la regle
    ignore_roi_if_entry_signal = False
    position_adjustment_enable = False
    process_only_new_candles = True
    startup_candle_count = 0                    # aucun indicateur technique : zero warm-up

    def leverage(self, pair, current_time, current_rate, proposed_leverage,
                 max_leverage, side, **kwargs) -> float:
        return 1.0                              # 1x : pas de levier dans l'experience

    def custom_stake_amount(self, pair, current_time, current_rate, proposed_stake,
                            min_stake, max_stake, leverage, entry_tag, side,
                            **kwargs) -> float:
        # 50 % de l'equite courante (donc compounding). Clampe par freqtrade sur [min,max].
        return float(self.wallets.get_total_stake_amount()) * STAKE_FRACTION

    def _macro_daily(self):
        """Regimes macro quotidiens (charges + caches une seule fois par run)."""
        if not hasattr(self, "_macro_cache"):
            d = Path(self.config.get("user_data_dir", "user_data")) / contracts.MACRO_DATA_DIR
            self._macro_cache = macro_regime.daily_regimes(macro_regime.load_history(d))
        return self._macro_cache

    def populate_indicators(self, df, metadata):
        daily = self._macro_daily()
        if len(daily) == 0:                     # fichiers macro absents => run inerte, jamais faux
            df[contracts.MACRO_REGIME_COL] = _NEUTRE
            return df
        df = regimes.attach_macro_regime(df, daily)
        # Avant la 1re date macro (et si une bougie tombe hors couverture) : NEUTRE = on ne fait
        # rien. Jamais PORTEUR/HOSTILE par defaut — un trou de donnees ne doit pas creer d'ordre.
        df[contracts.MACRO_REGIME_COL] = df[contracts.MACRO_REGIME_COL].fillna(_NEUTRE)
        return df

    def populate_entry_trend(self, df, metadata):
        reg = df[contracts.MACRO_REGIME_COL]
        # Signal d'ETAT, pas de transition : `enter_*` reste a 1 tant que le regime dure. Si
        # freqtrade refuse le flip sur la bougie de sortie, l'entree se fait a la suivante au
        # lieu d'etre perdue (auto-reparation ; le flip meme-bougie est verifie au smoke).
        df["enter_long"] = (reg == _PORTEUR).astype(int)
        df["enter_short"] = (reg == _HOSTILE).astype(int)
        df["enter_tag"] = reg.where(reg != _NEUTRE)
        return df

    def populate_exit_trend(self, df, metadata):
        reg = df[contracts.MACRO_REGIME_COL]
        bull, bear = reg == _PORTEUR, reg == _HOSTILE
        flat = (reg == _NEUTRE) if FLAT_ON_NEUTRE else False
        df["exit_long"] = (bear | flat).astype(int)     # bear => on vend le long
        df["exit_short"] = (bull | flat).astype(int)    # bull => on rachete le short
        return df
