"""GTA VI trophy rarity forecaster: earners-over-players, refresh-aware.

Idea: a trophy's Exophase rate is a ratio, earners / players_tracked.
Both sides move, and they move at different speeds: new players join
with zero trophies (dilution pulls every rate down) while the earners
of each trophy grow as the cohort plays through the game. So this
program never extrapolates the rate itself. It fits the growth of the
two counts separately in log time, then divides.

Counts are fitted on x = ln(1 + hours since launch), because launch
growth is fast at first and flattens out. Slopes are shrunk toward
their tier mean, because a trophy with four earners tells you almost
nothing on its own. When the whole history is flat (no read ever
changed) the recorder simply has not refreshed yet, so the program
assumes one refresh before the target instead of believing the flat
line. Spreads are per trophy: a random-walk term plus the jumpiness
actually seen in the history plus the fit residual, wider for
trophies with only a handful of earners.

Standard library only, no network, deterministic: same input bytes
always produce the same output bytes.
"""

import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

INPUT_DIR = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
OUTPUT_DIR = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))

LEVELS = [0.05, 0.25, 0.5, 0.75, 0.95]
ZS = [-1.645, -0.674, 0.0, 0.674, 1.645]
LAUNCH = datetime(2026, 11, 19, 0, 0, 0, tzinfo=timezone.utc)

# Ceiling (percent) no trophy's median may pass, by tier. Log-linear
# growth left alone would happily run a grind trophy to 100%.
CEILING = {"platinum": 3.0, "gold": 40.0, "silver": 25.0, "bronze": 95.0}

# Earners multiplier per tier when the history is perfectly flat and
# a single refresh is assumed before the target. Early-story bronze
# (first missions / early chapters) is caught up fastest.
FLAT_GROWTH = {"platinum": 2.0, "gold": 3.0, "silver": 2.5, "bronze": 4.0}
EARLY_WORDS = ("gone fishing", "chapter 1", "chapter 2", "chapter 3",
               "chapter 4")


def _clamp_pct(p):
    return min(99.99, max(0.01, p))


def _logit(pct):
    p = _clamp_pct(pct)
    return math.log(p / (100.0 - p))


def _inv_logit(lg):
    return 100.0 / (1.0 + math.exp(-lg))


def _round4(value):
    """Round to 4 decimals, half up, matching JS Math.round(x*1e4)/1e4."""
    scaled = value * 10000.0
    whole = math.floor(scaled)
    if scaled - whole >= 0.5:
        whole += 1
    out = whole / 10000.0
    return int(out) if float(out).is_integer() else out


def _hours_since_launch(stamp):
    """Hours from launch midnight to an ISO timestamp string."""
    try:
        moment = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return 0.0
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return (moment - LAUNCH).total_seconds() / 3600.0


def _x_of(stamp):
    return math.log1p(max(_hours_since_launch(stamp), 0.0))


def _fit_line(xs, ys):
    """Closed-form least squares; returns (slope, intercept, resid_var).

    Returns None when there are too few points or no spread in x.
    """
    n = len(xs)
    if n < 3:
        return None
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    sxx = sum((x - mean_x) ** 2 for x in xs)
    if sxx < 1e-12:
        return None
    sxy = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    slope = sxy / sxx
    intercept = mean_y - slope * mean_x
    resid = sum((y - (intercept + slope * x)) ** 2
                for x, y in zip(xs, ys)) / n
    return slope, intercept, resid


def _last_rates(case):
    """Last non-null rate per trophy, with tier-median / 0.63 fallbacks."""
    trophies = case["trophies"]
    hist = case["history"]
    last = [None] * len(trophies)
    for read in reversed(hist):
        rates = read.get("rates") or []
        for i in range(len(trophies)):
            if last[i] is None and i < len(rates) and rates[i] is not None:
                last[i] = float(rates[i])
        if all(v is not None for v in last):
            break
    by_tier = {}
    for i, trophy in enumerate(trophies):
        if last[i] is not None:
            by_tier.setdefault(trophy.get("tier", "bronze"), []).append(last[i])
    tier_med = {}
    for tier, vals in by_tier.items():
        vals = sorted(vals)
        tier_med[tier] = vals[len(vals) // 2]
    for i, trophy in enumerate(trophies):
        if last[i] is None:
            last[i] = tier_med.get(trophy.get("tier", "bronze"), 0.63)
    return last


def _history_is_flat(case):
    """True when no read ever changed: same players and same rates."""
    hist = case["history"]
    if len(hist) < 2:
        return True
    first_n = hist[0].get("players_tracked")
    first_rates = hist[0].get("rates") or []
    for read in hist[1:]:
        if read.get("players_tracked") != first_n:
            return False
        rates = read.get("rates") or []
        if len(rates) != len(first_rates):
            return False
        for a, b in zip(rates, first_rates):
            if a != b:
                return False
    return True


def _jump_variance(case):
    """Mean squared logit jump between consecutive reads.

    Exophase refreshes in jumps, not continuously. The size of the
    jumps seen so far is the honest extra spread for the next ones.
    Zero when nothing ever moved (the flat case is handled apart).
    """
    trophies = case["trophies"]
    hist = case["history"]
    squares = []
    for prev, cur in zip(hist, hist[1:]):
        pr, cr = prev.get("rates") or [], cur.get("rates") or []
        for i in range(min(len(trophies), len(pr), len(cr))):
            if pr[i] is None or cr[i] is None or pr[i] == cr[i]:
                continue
            d = _logit(float(cr[i])) - _logit(float(pr[i]))
            squares.append(d * d)
    if not squares:
        return 0.0
    return min(sum(squares) / len(squares), 1.0)


def _fit_players(case, x_target, xs_all):
    """Slope of ln(players) on log time, anchored at the last read."""
    hist = case["history"]
    xs, ys = [], []
    for k, read in enumerate(hist):
        n = read.get("players_tracked")
        if n is None or n <= 0:
            continue
        xs.append(xs_all[k])
        ys.append(math.log(float(n)))
    fit = _fit_line(xs, ys)
    if fit is None:
        return 0.0, float(hist[-1].get("players_tracked") or 1)
    slope = min(max(fit[0], 0.0), 1.5)
    x_last = xs[-1]
    n_last = float(hist[-1].get("players_tracked") or 1)
    n_pred = n_last * math.exp(slope * (x_target - x_last))
    return slope, max(n_pred, n_last)


def _fit_earners(case, x_target, x_last, last_rates, xs_all):
    """Per-trophy earners slope (shrunk to tier mean) and fit variance.

    Anchored at each trophy's last observed earner count so a shaky
    intercept cannot drag the forecast away from the data.
    """
    trophies = case["trophies"]
    hist = case["history"]
    raw = []
    for i, trophy in enumerate(trophies):
        xs, ys = [], []
        for k, read in enumerate(hist):
            rates = read.get("rates") or []
            n = read.get("players_tracked")
            if i >= len(rates) or rates[i] is None or not n:
                continue
            xs.append(xs_all[k])
            ys.append(math.log(float(rates[i]) * float(n) / 100.0 + 0.5))
        fit = _fit_line(xs, ys)
        raw.append(fit)
    tier_slopes = {}
    for i, trophy in enumerate(trophies):
        if raw[i] is not None:
            tier_slopes.setdefault(trophy.get("tier", "bronze"), []).append(
                min(max(raw[i][0], 0.0), 1.5))
    tier_mean = {t: sum(v) / len(v) for t, v in tier_slopes.items()}
    n_last = float(hist[-1].get("players_tracked") or 1)
    slopes, resid_vars = [], []
    for i, trophy in enumerate(trophies):
        fit = raw[i]
        if fit is None:
            slopes.append(tier_mean.get(trophy.get("tier", "bronze"), 0.3))
            resid_vars.append(0.0)
            continue
        own = min(max(fit[0], 0.0), 1.5)
        mean = tier_mean.get(trophy.get("tier", "bronze"), own)
        # Precision-weighted shrinkage: a trophy with hundreds of
        # earners has a slope worth trusting (early-story trophies grow
        # explosively — Chapter 1 went 8 -> ~7,200 earners in 2.5 days
        # on the live page); a trophy with a handful of earners does
        # not, so it leans on its tier mean. Weight caps at 0.9 so the
        # tier mean always keeps a say.
        earners_last = last_rates[i] * n_last / 100.0
        w = min(earners_last / (earners_last + 20.0), 0.9)
        slopes.append(w * own + (1.0 - w) * mean)
        resid_vars.append(min(fit[2], 0.5))
    return slopes, resid_vars


def _early_story(trophy):
    text = (trophy.get("name", "") + " " +
            trophy.get("description", "")).lower()
    return any(word in text for word in EARLY_WORDS)


def _forecast_case(case, name):
    if len(case.get("levels", [])) != 5:
        raise ValueError(name + " asks for levels other than five")
    hist = case["history"]
    if not hist:
        raise ValueError(name + " has no history")
    trophies = case["trophies"]
    last = _last_rates(case)
    n_last = float(hist[-1].get("players_tracked") or 1)
    horizon_days = float(case["horizon_minutes"]) / 1440.0
    x_target = _x_of(case.get("target") or "")
    x_last = _x_of(hist[-1].get("slot") or hist[-1].get("at") or "")
    # Log-time per read, computed once: _fit_earners used to re-parse
    # every read's timestamp for every trophy (55x336 parses on a full
    # final history), which dominated run time — the tie-break.
    xs_all = [_x_of(read.get("slot") or read.get("at") or "")
              for read in hist]
    base_spread = 0.6 * math.sqrt(horizon_days)
    flat = _history_is_flat(case)

    if flat:
        # One refresh is assumed before the target: the player base
        # jumps, and each trophy's earners grow by its tier factor.
        n_pred = n_last * 6.0
        jump_var = 0.36
        slopes = [0.0] * len(trophies)
        resid_vars = [0.0] * len(trophies)
    else:
        _slope_n, n_pred = _fit_players(case, x_target, xs_all)
        jump_var = _jump_variance(case)
        slopes, resid_vars = _fit_earners(case, x_target, x_last, last,
                                          xs_all)
    dx = x_target - x_last

    # A trophy every read shows at 100% while the tracked base grew a
    # lot is universal by construction: everyone counted holds it.
    # The kit's one observed refresh says exactly that ("every rate
    # but the one at 100% fell"). Trust the reads over the dilution
    # prior, but only when the reads themselves show it, so a flat
    # history (no growth observed) still takes the retention rule.
    n_first = float(hist[0].get("players_tracked") or n_last)
    universal = []
    for i in range(len(trophies)):
        seen = [float(read["rates"][i]) for read in hist
                if (read.get("rates") or []) and i < len(read["rates"])
                and read["rates"][i] is not None]
        universal.append(bool(seen) and min(seen) >= 99.99
                         and n_last >= 1.5 * n_first)

    rows = []
    for i, trophy in enumerate(trophies):
        tier = trophy.get("tier", "bronze")
        earners_last = last[i] * n_last / 100.0
        if not flat and universal[i]:
            earners_pred = 0.999 * n_pred
        elif flat:
            factor = 5.0 if (tier == "bronze" and _early_story(trophy)) \
                else FLAT_GROWTH.get(tier, 4.0)
            earners_pred = earners_last * factor
        elif last[i] > 90.0:
            # Near-universal trophies only fall by dilution: most new
            # players catch up, a fifth of the newcomers have not yet.
            earners_pred = earners_last + 0.8 * (n_pred - n_last)
        else:
            earners_pred = (earners_last + 0.5) * math.exp(slopes[i] * dx) - 0.5
        earners_pred = max(earners_pred, 0.0)
        earners_pred = min(earners_pred, 0.95 * n_pred)
        median = earners_pred / n_pred * 100.0
        median = min(median, CEILING.get(tier, 95.0))
        median = max(median, 0.01)
        if not flat and universal[i]:
            # The tier ceiling must not drag a proven-universal trophy
            # back down: every read showed 100% while the base grew,
            # and the live page still showed 100.00% two days later.
            # 99.95 (not 99.99) hedges the one way it can fall: brand-new
            # players who have not fished yet at the moment of the read.
            median = 99.95

        extra = 0.16 if earners_last < 10.0 else 0.0
        spread = math.sqrt(base_spread * base_spread + jump_var +
                           resid_vars[i] + extra)
        spread = min(max(spread, 0.3), 2.0)
        if not flat and universal[i]:
            # A trophy that never moved through a 6x refresh and two
            # more days of live reads has almost no uncertainty left:
            # a wide spread here is pure pinball loss.
            spread = 0.3
        centre = _logit(median)
        quantiles = []
        prev = 0.0
        for z in ZS:
            q = _round4(_inv_logit(centre + z * spread))
            q = min(max(float(q), 0.0), 100.0)
            q = max(q, prev)
            quantiles.append(q)
            prev = q
        rows.append({"id": trophy["id"], "q": quantiles})
    return {"trophies": rows}


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in sorted(INPUT_DIR.glob("*.in")):
        case = json.loads(path.read_text(encoding="utf-8"))
        forecast = _forecast_case(case, path.name)
        (OUTPUT_DIR / (path.stem + ".out")).write_text(
            json.dumps(forecast, separators=(",", ":")) + "\n",
            encoding="utf-8")


if __name__ == "__main__":
    main()
