# GTA VI Trophy Rarity Forecaster

Entry for make.fun `gta6-trophy-rarity-forecast-01`: forecast every GTA VI
trophy's Exophase earn rate at 2026-11-26T00:00:00Z as five quantiles,
scored by pinball loss on the logit scale.

## How it works

A rate is a ratio, `earners / players_tracked`, and the two sides move at
different speeds: new players join with zero trophies (dilution pulls
rates down) while earners grow as the cohort plays. So the program never
extrapolates the rate itself:

1. **E/N decomposition.** Fit `ln(players)` and, per trophy,
   `ln(earners + 0.5)` on `x = ln(1 + hours since launch)` with closed-form
   least squares, anchored at the last read. Slopes are shrunk 50/50 toward
   the tier mean. Rate = E_pred / N_pred.
2. **Flat-history fallback.** If no read ever changed, the recorder has
   not refreshed yet: assume one refresh before the target
   (N x6, earners x tier factor: early-story bronze 5.0, other bronze 4.0,
   silver 2.5, gold 3.0, platinum 2.0).
3. **Near-universal trophies.** A trophy at ~100% keeps the retention
   rule (newcomers catch up at 80%). Exception, proven by the reads: a
   trophy at 100% in every read while the tracked base grew 1.5x+ is
   universal by construction (the kit's one observed refresh: "every rate
   but the one at 100% fell") and is forecast at 99.9%.
4. **Tier ceilings.** Median capped: platinum 3%, gold 40%, silver 25%,
   bronze 95%. Earners capped at 95% of players.
5. **Adaptive spread.** Per trophy:
   `s = sqrt((0.5*sqrt(days))^2 + jump_var + fit_var + floor_extra)`,
   clipped to [0.3, 2.0]. `jump_var` is the mean squared logit jump
   between consecutive reads (0.36 when history is flat); `floor_extra`
   is 0.16 when the trophy has fewer than 10 earners. Quantiles are
   `inv_logit(logit(median) + z*s)`, `z = [-1.645, -0.674, 0, 0.674, 1.645]`,
   rounded half-up to 4 decimals.

## Run

```sh
mkdir -p out && MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

Python 3.13 standard library only, no network, deterministic
(two runs are byte-identical), ~25-35 ms per case.

## Files

- `main.py` — the whole forecaster (single file, no imports beyond stdlib)
- `LICENSE` — MIT
- `TEST-REPORT.md` — test numbers and honest self-review
