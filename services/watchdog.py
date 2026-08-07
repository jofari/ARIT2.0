"""M10 - services/watchdog.py : le dernier filet (docs/M10, docs/11).

Defense en profondeur : ligne 1 = stoploss_on_exchange (Binance), ligne 2 = ce watchdog.
Couvre le cas ou la gestion continue S'ARRETE (crash/freeze du bot).

INDEPENDANCE TOTALE (M10 invariant 1) : AUCUN import du projet (ni arit_lib, ni freqtrade,
ni la DB freqtrade). Fichiers + exchange only. Le watchdog doit survivre a tout bug d'ARIT ;
ses constantes sont donc definies ICI (copies documentees de params.py, valeurs identiques).

Ses clefs ccxt : trade-only, sans retrait, distinctes de celles de freqtrade (M10 invariant 2),
via env. Webhook Discord direct (ce process a le droit au reseau). Chaque action est loggee
en local (le watchdog est lui-meme auditable, M10 invariant 3).
"""

import logging
import os
import time
from pathlib import Path

import ccxt
import requests

logger = logging.getLogger(__name__)

# --- Constantes (miroir documente de params.py ; le watchdog n'importe PAS le projet).
HEARTBEAT_MAX_S = 600        # params.WATCHDOG_HEARTBEAT_MAX_S (PDR 09.5 / M10) : > 10 min
LOOP_S = 60                  # params.WATCHDOG_LOOP_S (M10) : boucle 60 s
CONFIRM_READS = 2            # params.WATCHDOG_CONFIRM_READS (M10) : 2 lectures avant d'agir
# miroir params.WATCHDOG_DUST_THRESHOLD_USDT (valeur actee build, non fixee par le PDR)
DUST_THRESHOLD_USDT = 1.0
STAKE_CURRENCY = "USDT"      # params.STAKE_CURRENCY
HTTP_TIMEOUT_S = 10

# Fichier d'etat partage (docs/11.3) : mtime du heartbeat, chemin relatif a user_data/.
HEARTBEAT_REL = "state/heartbeat"
# Flag local d'idempotence du flatten (interne au watchdog, reset manuel - M10).
FLATTEN_FLAG_REL = "state/watchdog_flattened"

# --- Env (aucune valeur en dur).
API_KEY_ENV = "WATCHDOG_API_KEY"
API_SECRET_ENV = "WATCHDOG_API_SECRET"
EXCHANGE_ENV = "WATCHDOG_EXCHANGE"        # defaut binance
WEBHOOK_ENV = "DISCORD_WEBHOOK_URL"       # webhook Discord direct
FLATTEN_ENV = "WATCHDOG_FLATTEN"          # "true" => flatten autorise (defaut false)

LEVEL_CRITICAL = "CRITICAL"
LEVEL_WARNING = "WARNING"

# Repertoire user_data/ (override en test via set_user_data_dir).
_DEFAULT_USER_DATA_DIR = Path(__file__).resolve().parents[1] / "user_data"
_USER_DATA_DIR = None


def set_user_data_dir(path) -> None:
    """Fixe le repertoire user_data/ (tests: tmp_path)."""
    global _USER_DATA_DIR
    _USER_DATA_DIR = Path(path)


def _base() -> Path:
    return _USER_DATA_DIR or _DEFAULT_USER_DATA_DIR


def _heartbeat_path() -> Path:
    return _base() / HEARTBEAT_REL


def _flatten_flag() -> Path:
    return _base() / FLATTEN_FLAG_REL


def _flatten_enabled() -> bool:
    return os.environ.get(FLATTEN_ENV, "false").strip().lower() == "true"


# ----------------------------------------------------------------- lectures
def heartbeat_age(path) -> float:
    """now - mtime(heartbeat), en secondes. inf si le fichier est absent/illisible (=> alerte)."""
    try:
        return time.time() - os.path.getmtime(path)
    except OSError:
        return float("inf")


def _value_usdt(client, asset, amount):
    """Valeur USDT d'un solde via fetch_ticker, ou None si indisponible."""
    try:
        ticker = client.fetch_ticker(f"{asset}/{STAKE_CURRENCY}")
        price = ticker.get("last") or ticker.get("close")
        if price is None:
            return None
        return float(price) * float(amount)
    except Exception as exc:
        logger.warning("watchdog: prix indisponible pour %s (%s)", asset, exc)
        return None


def open_exposure(ccxt_client) -> list:
    """Soldes non-USDT valorises au-dessus du dust (spot = pas de 'positions'). Liste vide sinon."""
    try:
        balance = ccxt_client.fetch_balance()
    except Exception as exc:
        logger.error("watchdog: fetch_balance echec (%s)", exc)
        return []
    totals = balance.get("total", {}) if isinstance(balance, dict) else {}
    holdings = []
    for asset, amount in totals.items():
        if asset == STAKE_CURRENCY or not amount:
            continue
        value = _value_usdt(ccxt_client, asset, amount)
        if value is None or value < DUST_THRESHOLD_USDT:
            continue
        holdings.append({"asset": asset, "amount": float(amount), "value_usdt": value})
    return holdings


# ----------------------------------------------------------------- actions
def _webhook_url():
    """URL du webhook : environnement d'abord, sinon .env lu DIRECTEMENT.

    Lecture inline et non `services/env_local.py` : M10 invariant 1 interdit tout import du
    projet a ce fichier, et assume explicitement la duplication (cf. ses constantes). Le
    dernier filet ne doit dependre de rien.

    Sans cette relecture, `alert()` sortait en SILENCE (2026-08-07) : les secrets ne vivent
    que dans `.env`, que rien ne chargeait dans l'environnement des services lances par
    start_arit.py. Le watchdog tournait, ne voyait pas d'URL, et n'alertait jamais — la
    panne la plus couteuse possible pour un filet de securite.
    """
    url = os.environ.get(WEBHOOK_ENV)
    if url:
        return url.strip()
    try:
        lignes = (Path(__file__).resolve().parents[1] / ".env").read_text(
            encoding="utf-8").splitlines()
    except OSError:
        return None
    for ligne in lignes:
        ligne = ligne.strip()
        if ligne.startswith(f"{WEBHOOK_ENV}="):
            return ligne.split("=", 1)[1].strip().strip('"').strip("'") or None
    return None


def alert(level, msg) -> None:
    """Webhook Discord direct + log local (le watchdog est auditable, M10 invariant 3)."""
    line = f"[watchdog][{level}] {msg}"
    logger.warning(line)
    url = _webhook_url()
    if not url:
        logger.error("watchdog: aucun webhook (%s absent de l'env ET de .env) - "
                     "ALERTE NON ENVOYEE", WEBHOOK_ENV)
        return
    try:
        rep = requests.post(url, json={"content": line}, timeout=HTTP_TIMEOUT_S)
    except Exception as exc:
        logger.error("watchdog: webhook echec (%s) - ALERTE NON ENVOYEE", exc)
        return
    # Le code HTTP n'etait pas verifie (2026-08-07) : un webhook revoque (401), supprime
    # (404) ou limite (429) renvoie une reponse SANS lever, donc l'alerte disparaissait en
    # silence. Meme classe de panne que celles corrigees ce jour — un filet de securite ne
    # doit jamais echouer sans le dire. L'URL n'est JAMAIS journalisee (c'est un secret).
    if rep.status_code >= 300:
        logger.error("watchdog: webhook refuse (HTTP %s) - ALERTE NON ENVOYEE : %s",
                     rep.status_code, (rep.text or "")[:200])


def flatten(ccxt_client, holdings) -> None:
    """cancel open orders + market-sell de chaque holding. IDEMPOTENT : ne flatten jamais deux
    fois (flag pose au 1er declenchement, reset manuel - M10). Chaque action est loggee."""
    flag = _flatten_flag()
    if flag.exists():
        logger.info("watchdog: flatten deja effectue (flag present), no-op")
        return
    for holding in holdings:
        symbol = f"{holding['asset']}/{STAKE_CURRENCY}"
        try:
            ccxt_client.cancel_all_orders(symbol)
        except Exception as exc:
            logger.error("watchdog: cancel_all_orders %s echec (%s)", symbol, exc)
        try:
            ccxt_client.create_market_sell_order(symbol, holding["amount"])
            logger.warning("watchdog: market-sell %s %s", holding["amount"], symbol)
        except Exception as exc:
            logger.error("watchdog: market-sell %s echec (%s)", symbol, exc)
    try:
        flag.parent.mkdir(parents=True, exist_ok=True)
        flag.touch()
    except OSError as exc:
        logger.error("watchdog: pose du flag flatten echec (%s)", exc)


# ---------------------------------------------------- logique anti-faux-positif
def is_breach(age, holdings) -> bool:
    """Condition de breach : heartbeat trop vieux ET exposition non nulle (M10).

    Reste le declencheur du FLATTEN : on ne liquide que ce qui existe. Ne pas confondre
    avec `bot_silencieux`, qui declenche l'ALERTE et n'exige aucune exposition.
    """
    return age > HEARTBEAT_MAX_S and bool(holdings)


def bot_silencieux(age) -> bool:
    """Heartbeat trop vieux, INDEPENDAMMENT de l'exposition (correctif 2026-08-07).

    Pourquoi separer : en dry-run il n'y a aucune position reelle, et sans clefs ccxt
    (« mode alerte seule ») `open_exposure` renvoie toujours []. `is_breach` etait donc
    TOUJOURS faux et le watchdog n'alertait JAMAIS, meme bot mort — un dry-run non
    surveille serait reste muet pendant des semaines.

    Le flatten, lui, continue d'exiger une exposition (`is_breach`) : liquider n'a de sens
    que s'il y a quelque chose a liquider. On separe donc « prevenir » de « agir », au lieu
    d'affaiblir M10.
    """
    return age > HEARTBEAT_MAX_S


def next_consecutive(breached, consecutive) -> int:
    """Compteur de lectures consecutives en breach (reset des que la condition retombe)."""
    return consecutive + 1 if breached else 0


def ready_to_act(consecutive) -> bool:
    """Anti-faux-positif : agir seulement apres CONFIRM_READS lectures a 60 s d'intervalle."""
    return consecutive >= CONFIRM_READS


# ----------------------------------------------------------------- boucle
def _make_client():
    """Client ccxt trade-only depuis l'env, ou None si clefs absentes (dry : alerte seule)."""
    key = os.environ.get(API_KEY_ENV)
    secret = os.environ.get(API_SECRET_ENV)
    if not key or not secret:
        logger.warning("watchdog: clefs ccxt absentes - mode alerte seule")
        return None
    exchange_id = os.environ.get(EXCHANGE_ENV, "binance")
    try:
        exchange_cls = getattr(ccxt, exchange_id)
        return exchange_cls({"apiKey": key, "secret": secret, "enableRateLimit": True})
    except Exception as exc:
        logger.error("watchdog: init ccxt echec (%s)", exc)
        return None


def _handle_breach(client, holdings, age) -> None:
    """Breach confirme : alerte CRITICAL ; flatten seulement si active et pas deja fait."""
    detail = ", ".join(f"{h['asset']}={round(h['value_usdt'], 2)} USDT" for h in holdings)
    alert(LEVEL_CRITICAL, f"heartbeat {int(age)}s > {HEARTBEAT_MAX_S}s, exposition: {detail}")
    if _flatten_enabled() and client is not None and not _flatten_flag().exists():
        flatten(client, holdings)
        alert(LEVEL_CRITICAL, f"flatten declenche sur: {detail}")


def surveiller_liveness(age, muet_depuis, alerte_posee) -> tuple:
    """Etat de l'alerte « bot silencieux ». -> (muet_depuis, alerte_posee).

    Une SEULE alerte par episode, et une seule a la reprise : sans ca, un bot mort le 2e
    jour d'une absence de trois semaines produirait ~30 000 messages Discord. Meme garde
    anti-faux-positif que le flatten (CONFIRM_READS lectures a LOOP_S d'intervalle).
    """
    muet_depuis = next_consecutive(bot_silencieux(age), muet_depuis)
    if ready_to_act(muet_depuis) and not alerte_posee:
        alert(LEVEL_CRITICAL, f"bot SILENCIEUX depuis {int(age)}s "
                              f"(heartbeat > {HEARTBEAT_MAX_S}s) - dry-run a l'arret ?")
        return muet_depuis, True
    if muet_depuis == 0 and alerte_posee:
        alert(LEVEL_WARNING, "bot de nouveau vivant (heartbeat frais)")
        return muet_depuis, False
    return muet_depuis, alerte_posee


def main_loop() -> None:
    """Boucle 60 s : controle heartbeat + exposition, 2 lectures avant d'agir (M10)."""
    client = _make_client()
    consecutive = 0
    muet_depuis, alerte_posee = 0, False
    while True:
        try:
            age = heartbeat_age(_heartbeat_path())
            holdings = open_exposure(client) if client is not None else []
            # ALERTE : independante de l'exposition (sinon muette en dry-run, cf.
            # bot_silencieux). FLATTEN : exige toujours une exposition (is_breach).
            muet_depuis, alerte_posee = surveiller_liveness(age, muet_depuis, alerte_posee)
            consecutive = next_consecutive(is_breach(age, holdings), consecutive)
            if ready_to_act(consecutive):
                _handle_breach(client, holdings, age)
        except Exception as exc:
            logger.error("watchdog: iteration echec (%s)", exc)
        time.sleep(LOOP_S)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main_loop()
