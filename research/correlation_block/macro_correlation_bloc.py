"""PROPOSITION — bloc "correlation / sentiment du risque" pour la couche macro.

STATUT : PROPOSITION, non fusionnee. Gouvernance PDR "on propose, on n'applique
pas" : aucun fichier de `user_data/strategies/arit_lib/`, `docs/` ou `params.py`
n'a ete touche. A fusionner dans `arit_lib/macro_regime.py` APRES decision signee.

Rapport : `research/correlation_block/RAPPORT.md`
Tests   : `research/correlation_block/test_correlation_bloc.py`

POURQUOI PAS UN 6e COMPOSANT DE SCORE
-------------------------------------
Le regime macro est une SOMME de 5 composants dans {-1, 0, +1} avec
PORTEUR >= +2 / HOSTILE <= -2 (macro_regime.daily_regimes). Un 6e terme additif
poserait 3 problemes :

1. Il deplacerait silencieusement le sens des seuils (+-2 sur 5 -> +-2 sur 6) :
   HOSTILE deviendrait mecaniquement plus facile a atteindre, ce qui recalibre
   les 5 composants existants sans les avoir touches.
2. Un score dans {-1, 0, +1} est SYMETRIQUE par construction. Or la mesure dit
   que le BTC suit les actions a la BAISSE mais pas a la hausse : un +1 quand le
   SPX monte est precisement ce qu'il ne faut pas coder.
3. Motif deja mesure 3 fois sur ce projet (funding en score, sizing par la force
   du score, penalite continue de regime) : un signal utile en VETO detruit de la
   valeur en TERME ADDITIF.

=> Le bloc sort un VETO booleen, journalise a part, ablatable independamment.
   Le score des 5 composants n'est pas touche.

ARCHITECTURE
------------
c6  risk-off actions  : le SPX casse sa structure a la baisse -> veto longs.
c7  regime de correlation (META) : rho(BTC, SPX) decide si c6 est ARME.
    rho eleve  => le BTC se traite comme un actif de risque, le veto a du sens.
    rho faible => le BTC suit ses propres drivers, bloquer sur le SPX = bruit.

Point-in-time : identique au reste du module (decalage +1 jour applique par
`daily_regimes`). Aucune valeur du jour J n'est lisible avant J+1 00:00 UTC.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from arit_lib import params

# -------------------------------------------------------------------- constantes
# A DEPLACER dans params.py avant fusion (interdit n4 : zero valeur magique hors
# params.py). Chaque valeur porte sa source, convention params.py.
MACRO_SPX_FILE = "sp500.csv"          # 06.2 c6 — FRED SP500, meme parser que dxy
MACRO_SPX_BREAK_WINDOW_D = 20         # 06.2 c6 — plus-bas de cloture sur 20 j ouvres
MACRO_CORR_WINDOW_FAST_D = 30         # 06.2 c7 — rho court (sessions US)
MACRO_CORR_WINDOW_SLOW_D = 90         # 06.2 c7 — rho long, confirmation
MACRO_CORR_ARM_ABOVE = 0.50           # 06.2 c7 — hysteresis : armement du veto
MACRO_CORR_DISARM_BELOW = 0.30        # 06.2 c7 — hysteresis : desarmement
MACRO_EQUITY_STALE_HOURS = 120        # 06.2 c6 — serie 5/7 : 48 h ne suffit pas
                                      # (feries US -> jusqu'a 96 h sans obs)

# Etats du regime de correlation (c7).
CORR_COUPLED = "COUPLE"
CORR_TRANSITION = "TRANSITION"
CORR_DECOUPLED = "DECOUPLE"
MACRO_CORR_STATES = (CORR_COUPLED, CORR_TRANSITION, CORR_DECOUPLED)

# Raisons journalisees. Chaines STABLES et sans interpolation : elles sont
# COMPTEES telles quelles dans l'ablation (interdit n6, chaque evaluation journalisee).
EQUITY_VETO_BINDING = "equity_risk_off"                # bloque, et bloque SEUL
EQUITY_VETO_REDUNDANT = "equity_risk_off_redundant"    # bloque, macro deja HOSTILE
EQUITY_PASS_DECOUPLED = "equity_decoupled"             # rho bas -> veto desarme
EQUITY_PASS_NO_BREAK = "equity_no_break"               # arme, mais pas de cassure
EQUITY_PASS_STALE = "equity_stale"                     # donnee absente -> fail-open


# --------------------------------------------------------------------- c6 : risk-off
def equity_structural_break(spx: pd.Series,
                            window: int = MACRO_SPX_BREAK_WINDOW_D) -> pd.Series:
    """True quand le SPX cloture sous son plus-bas de cloture des `window` j ouvres.

    `shift(1)` exclut le jour courant de son propre plancher : la cassure est un
    evenement, pas une tautologie. Index = sessions US uniquement (le passage au
    calendrier 7/7 est le role de `align_to_calendar`).

    ASYMETRIQUE PAR CONSTRUCTION : aucune sortie "haussiere" n'existe. Le symetrique
    (SPX casse un plus-haut => +1) est explicitement ECARTE — la correlation coute
    dans un sens et ne rapporte pas dans l'autre (RAPPORT §2).
    """
    floor_ = spx.shift(1).rolling(window).min()
    return (spx < floor_).fillna(False)


# ------------------------------------------------------------------- c7 : correlation
def btc_equity_correlation(btc_daily_close: pd.Series, spx: pd.Series,
                           window: int) -> pd.Series:
    """rho de Pearson des rendements log BTC/SPX, calcule SUR LES SESSIONS US.

    PIEGE EVITE : calculer rho sur un calendrier 7/7 avec un SPX forward-fille
    injecte ~2 jours de rendement NUL par semaine cote SPX, ET desaligne les
    fenetres (le lundi, le BTC rend 1 jour quand le SPX rend le week-end entier).

    Effet MESURE par simulation (test `test_rho_calendaire_est_deflate...`,
    modele : facteur de risque latent 7/7, SPX ferme le week-end et pricant
    samedi+dimanche+lundi a la seance du lundi) : rho calendaire ~= 0,66 x rho
    sessions, soit environ -33 %. Un vrai couplage a 0,75 s'afficherait a 0,50 —
    pile sur le seuil d'armement, donc un veto qui clignote ou ne s'arme jamais.
    (Chiffre de simulation, pas de mesure sur donnees reelles : a re-derivier sur
    l'historique BTC/SPX avant fusion.)

    Le rendement BTC vendredi->lundi couvre le week-end : c'est la bonne fenetre,
    elle correspond a celle du SPX sur le meme intervalle.
    """
    sessions = spx.index
    btc_on_sessions = btc_daily_close.reindex(sessions).ffill()
    r_btc = np.log(btc_on_sessions).diff()
    r_spx = np.log(spx).diff()
    return r_btc.rolling(window).corr(r_spx)


def correlation_state(rho_fast: pd.Series, rho_slow: pd.Series) -> pd.Series:
    """rho -> {COUPLE, TRANSITION, DECOUPLE} avec hysteresis.

    Sans hysteresis, un rho qui oscille autour d'un seuil unique fait clignoter le
    veto d'un jour a l'autre. Bande morte : on ARME au-dessus de 0,50 (confirme par
    le rho long), on ne DESARME qu'en repassant sous 0,30, et on garde l'etat
    precedent entre les deux. Avant tout etat etabli => TRANSITION (veto desarme,
    cf. `evaluate`), donc le warm-up ne bloque aucune entree.
    """
    arm = (rho_fast >= MACRO_CORR_ARM_ABOVE) & (rho_slow >= MACRO_CORR_DISARM_BELOW)
    disarm = rho_fast < MACRO_CORR_DISARM_BELOW

    state = pd.Series(np.nan, index=rho_fast.index, dtype="object")
    state[arm] = CORR_COUPLED
    state[disarm] = CORR_DECOUPLED
    return state.ffill().fillna(CORR_TRANSITION)


# ------------------------------------------------------------------------ alignement
def align_to_calendar(sessions_series: pd.Series, full_index: pd.DatetimeIndex,
                      stale_hours: int = MACRO_EQUITY_STALE_HOURS) -> pd.DataFrame:
    """Sessions US -> calendrier 7/7. -> DataFrame(value, fresh).

    `value` est forward-fillee depuis la derniere session ; `fresh` dit si cette
    derniere session a moins de `stale_hours`. Les deux colonnes sont necessaires :
    `evaluate` doit distinguer "pas de cassure" de "on ne sait pas".

    ⚠️ Pourquoi une fenetre DEDIEE et pas MACRO_STALE_HOURS (48 h) : le SPX est une
    serie 5/7. Un ferie US colle a un week-end laisse jusqu'a 96 h sans observation
    -> le composant tomberait stale ~10 fois par an pour une raison purement
    calendaire. Or `dxy` (DTWEXBGS) est DEJA 5/7 et tombe stale les memes jours :
    avec MACRO_STALE_FAILSAFE = 3, ajouter UNE serie 5/7 fait passer le compteur de
    1 a 2. Il ne reste qu'un cran de marge avant que chaque ferie US ne bascule le
    regime en HOSTILE par fail-safe — raison pour laquelle ce bloc n'ajoute QUE le
    SPX, et pas SPX + NDX (RAPPORT §3).
    """
    obs_dates = pd.Series(sessions_series.index, index=sessions_series.index)
    value = sessions_series.reindex(full_index.union(sessions_series.index)).ffill()
    last_obs = obs_dates.reindex(full_index.union(sessions_series.index)).ffill()

    value = value.reindex(full_index)
    last_obs = last_obs.reindex(full_index)
    age_h = (pd.Series(full_index, index=full_index) - last_obs) / pd.Timedelta(hours=1)
    fresh = last_obs.notna() & (age_h <= stale_hours)
    return pd.DataFrame({"value": value, "fresh": fresh})


# --------------------------------------------------------------------- decision c6+c7
def evaluate(equity_break: bool, corr_state: str, macro_regime: str,
             data_fresh: bool) -> tuple[bool, str]:
    """Compose c6 + c7 -> (bloquer_nouveaux_longs, raison journalisable).

    Les 4 arbitrages, et leur justification (tous revisables — RAPPORT §5) :

    1. ARMEMENT SUR `COUPLE` SEUL. TRANSITION est la bande morte de l'hysteresis,
       c'est-a-dire "on ne sait pas". Armer sur l'incertitude rendrait le meta-gate
       inutile (le veto serait actif presque tout le temps) et couterait des entrees
       valides. Le veto doit etre precis, pas large.

    2. FAIL-OPEN SUR DONNEE PERIMEE. `regime_now` porte deja un fail-safe global
       (>= 3 composants stale => HOSTILE) qui couvre la perte systemique de donnees.
       Empiler un second fail-safe sur une serie 5/7 le ferait tirer ~10 fois par an
       pour un motif calendaire, sans contenu informationnel. Pire : un filtre qui
       bloque sur donnee absente devient INFALSIFIABLE en ablation — on ne pourrait
       plus separer la valeur du filtre de celle du trou de donnees.
       ⚠️ C'est la decision la plus discutable des quatre ; l'alternative fail-safe
       se defend si la priorite est la securite plutot que la mesurabilite.

    3. RAISONS DISTINCTES ET STABLES, jamais d'f-string. Elles sont comptees telles
       quelles dans l'ablation.

    4. BINDING vs REDUNDANT. Quand la macro est deja HOSTILE, l'entree est bloquee
       en amont : le veto actions n'ajoute rien ce jour-la. Compter les deux cas
       separement donne directement l'apport MARGINAL du filtre (= nombre de
       BINDING), qui est la seule quantite decisionnelle. Sans cette distinction,
       l'ablation surestime le filtre de tous ses blocages non-liants.
    """
    if not data_fresh:
        return False, EQUITY_PASS_STALE
    if corr_state != CORR_COUPLED:
        return False, EQUITY_PASS_DECOUPLED
    if not equity_break:
        return False, EQUITY_PASS_NO_BREAK
    if macro_regime == params.MACRO_REGIMES[2]:  # HOSTILE
        return True, EQUITY_VETO_REDUNDANT
    return True, EQUITY_VETO_BINDING
