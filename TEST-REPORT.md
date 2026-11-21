# TEST REPORT — gta6-trophy-rarity-forecast-01 entry

Built 21 Nov 2026, ~17:22–18:00 WIB. `main.py` (Python 3.13 stdlib only,
no network, deterministic). No repo created, no submit made by the builder.

## 1. Practice cases p00 / p01 (kit input)

- Format: both `.out` JSON valid, exactly one top key `trophies`, 55 rows,
  55 distinct ids, every `q` five finite numbers in [0, 100],
  non-decreasing, 2,752 bytes each (limit 65,536). PASS.
- Median range: 0.21% – 83.33%. q05 min 0.0631%, q95 max 93.20%.
- Samples (p00): id 1 platinum `[0.0631, 0.1283, 0.21, 0.3435, 0.6965]`;
  id 2 (100% trophy) `[64.5941, 76.7876, 83.3333, 88.3141, 93.1988]`;
  id 7 gold final mission `[0.1656, 0.3366, 0.55, 0.8976, 1.81]`.
- p00 and p01 outputs are identical: expected, their histories differ by
  one extra read that is flat-identical to the rest.
- **Practice loss CANNOT be computed locally — the practice answers are
  not in the kit.** Any local "practice loss" number would be invented.
  The kit only states the persistence baseline's practice loss: 1.51.

## 2. Determinism + runtime

- Two full runs over both cases: `diff -r` identical. PASS.
- Runtime: 0.049–0.070 s for both cases together (~25–35 ms per case),
  target <150 ms. PASS. (Tie-break is run_ms, so speed is free ranking.)

## 3. Synthetic holdouts (my own worlds — NOT practice scores)

Scorer: exact pinball-on-logit from the kit
(`2*max(tau*d, (tau-1)*d)`, `d = logit(y) - logit(q)`, clamp [0.01, 99.99]).

| Set | World | Model loss | Persistence loss | Model miss / cov | Persist. miss / cov |
|-----|-------|-----------|------------------|------------------|---------------------|
| synA | N x3 in history, 24 h horizon, tier slopes | 0.1067 | 0.1133 | 0.05 pp / 1.00 | 0.11 pp / 1.00 |
| synB | N x6 in history, 24 h horizon, tier slopes | 0.1068 | 0.1066 | 0.06 pp / 1.00 | 0.02 pp / 1.00 |
| synC | Flat history, N x6 at target, earners x1.2–3.0, trophy 2 stays 100% | 0.4628 | 1.0044 | 0.57 pp / 0.98 | 0.57 pp / 0.00 |
| synD | N x3, trophy 2 at 100% in every read, truth 100% | 0.1386 | 0.1123 | 0.01 pp / 0.98 | 0.11 pp / 0.98 |

Reading: in smooth log-time worlds (synA/synB) the model is essentially
tied with persistence — the extra spread costs about what the better
median gains. The edge lives in the refresh regime (synC): 0.46 vs 1.00,
and 0.34 vs 1.02 excluding trophy 2. Coverage 0.98 vs persistence 0.00
there. synD validates the universal-trophy branch (q50 99.9 after the fix;
before the fix the tier ceiling dragged it to 95.0 and loss was 0.2106).

## 4. Edge cases

- 1-read history + two null rates: exit 0, 55 valid rows, null trophies
  fall back to tier medians. PASS.

## 5. Self-review (jujur)

1. **Aneh tidak?** Mostly no. Medians move in the right direction
   (floor trophies ~0.2%, 100% trophy down to 83% in the flat case,
   grind trophies low). One honest oddity: synB ties persistence —
   in a smooth world our wider spread eats the median gain. That is the
   intended trade (jumps are certain in a 4.5-day final; smoothness is
   not), but it means we have no edge if the final turns out smooth.
2. **Ada yang kurang tidak?** Yes. (a) The trend path — the one that
   matters for the final — was only tested on synthetic worlds built on
   the same log-time assumptions as the model: circularity risk, the
   numbers above are not a real holdout. (b) The flat-fallback tier
   factors (5.0/4.0/2.5/3.0/2.0) are priors, not fitted; synC shows the
   model still wins 2x with wrong factors, which mitigates but does not
   remove this. (c) Spread is principled, not tuned against a real
   jump holdout. (d) No live quota check, no repo, no `makefun check` —
   those steps are still open and must happen in a recorded session.
3. **Bisa ngalahin house + masuk top 20 final tidak?** Against the
   persistence baseline: yes, clearly, in any world with a refresh
   (synC 0.46 vs 1.00; practice baseline is 1.51 and the flat fallback
   moves medians most of the way toward the refreshed truth). Against
   the house superbot: unknown — it gets one max-effort call on the
   final case and may use the same E/N structure. Top 20 of 11,437
   (0.17%) is a high bar and many entries share the E/N idea; **no #1
   promise**. Realistic: competitive for top 20 IF the final history
   shows several refreshes (likely over 2 days) and the trend fit holds;
   weak if the final answer is dominated by one unforecastable jump.

## 6. Remaining risks (for the submit decision)

- R1 — Daily quota: the alignment note says two slots were already used
  today by the news-image round 2 submit. Real cap is 3/day, not the
  advertised 10. **Verify live quota before any submit.**
- R2 — Trophy 2 (100%) in a flat history still uses retention (83.33%).
  In the final the history will not be flat, so the universal branch
  (tested in synD) should fire if it truly stays 100%. If the final
  history is somehow flat, that 83.33% costs ~0.13 mean loss if the
  truth stays 100%.
- R3 — Transcript/authorship gates: `main.py` was written fresh in 6
  agent messages (3 writes + 3 edits, own structure/names). The repo,
  `makefun compress` / `makefun check`, and submit must still be done
  in a recorded session starting after the 19 Nov 11:30 UTC opening.
- R4 — House superbot final score is unknown until grading; the prize
  needs a strictly lower loss than the best house entry AND a top-20 rank.

## 7. Improvement v2 (21 Nov ~17:50 WIB) — live-page backtest, real data

The kit's practice answers are not in the kit, so no local practice loss
exists. But the source page is public, so the improvement was measured
against the LIVE Exophase page, crawled 21 Nov 10:43 UTC: all 55 current
rates (sum 157.89 vs 147.78 at the 638 era; the 100% trophy still
100.00%). Backtest: run the model on the p00 flat history (last read
19 Nov 02:30Z, 638 players) with target = the live crawl, horizon
3,373 min (~2.5 days), score pinball-logit vs the live rates. This is a
REAL out-of-sample holdout, not a synthetic world built on the model's
own assumptions.

| Variant | Loss vs live rates |
|---------|-------------------|
| Persistence (last rates) | 3.1183 |
| Model v1 (base spread 0.5) | 2.1885 |
| Model v2 (base spread 0.6) | 2.1229 |
| v2 + spread x1.25 (post-hoc) | 1.9671 |
| v2 + universal-tight (post-hoc) | 2.0246 |
| v2 + median x0.7 (post-hoc) | 1.9189 |

Findings, and what was (not) changed:
- The model beats persistence by ~0.93 on a real 2.5-day move. The edge
  is real, not just synthetic.
- Spread was TOO NARROW on the real move (widening keeps helping up to
  x1.6 in the sweep). Changed: base spread coefficient 0.5 -> 0.6
  (total spread ~13% wider on the final horizon). NOT chased further:
  the sweep is confounded by the flat path's median bias (below), and
  the final runs the trend path, whose spread is already larger.
- Universal trophy: worst single error in v1's flat path (median 83.33
  vs live 100.00), and in synD v1 lost to persistence (0.1386 vs
  0.1123). Changed (trend path only, the one the final uses): median
  99.9 -> 99.95 and spread pinned to 0.3. Verified on a synthetic
  non-flat case: quantiles [99.9181, 99.9388, 99.95, 99.9591, 99.9695].
  Live evidence: the trophy stayed 100.00% through a 6x refresh and two
  more days — a wide spread on it is pure loss.
- Median x0.7 also helps on this backtest (1.92) — NOT applied. It is a
  flat-path artifact (N x6 prior + earner factors overestimate rates
  when the real player growth is larger); the final runs the trend path,
  which fits N and E from the actual reads instead of priors. Applying a
  global 0.7 median scale to the trend path would be overfitting to the
  flat path's failure mode.
- Re-verified after the change: p00/p01 valid (55 rows, non-decreasing,
  in range), two runs byte-identical, runtime 0.055 s for both cases.
  Backtest v2: 2.1229 (was 2.1885).

Honest limit: this backtest exercises the FLAT path (the only path a
flat practice history triggers). The final runs the TREND path, so the
backtest validates the spread/universal direction, not the trend fit
itself. No #1 promise — same as before, but the two changes are each
grounded in live evidence, not in a synthetic world.

## 8. Improvement v3 (21 Nov ~17:55 WIB) — precision-weighted slope shrinkage

Problem: the trend path (the one the final uses) shrank every trophy's
earner slope 50/50 toward its tier mean. That is fine for a trophy with
4 earners, but it halves the slope of early-story trophies whose growth
is explosive and well-measured — Chapter 1 went 8 -> ~7,200 earners in
2.5 days on the live page, and the 50/50 shrink was dragging its day-7
median down (14.93% on a reconstructed full history, below the 18.02%
already seen live — i.e. v2 predicted Chapter 1 would FALL by day 7,
against its whole trajectory).

Change (`_fit_earners`): slope = w*own + (1-w)*tier_mean with
w = min(E_last / (E_last + 20), 0.9). A trophy with hundreds of earners
trusts its own slope; a trophy with a handful leans on its tier mean.
The 0.9 cap keeps the tier mean a say in every case.

Sensitivity (reconstructed plausible final history: p00 reads + 04:30
refresh rebuilt from the kit's stated post-refresh sum 110.55 +
log-interpolated reads to the live page, N_live estimated ~40,000 from
the 0.01% floor constraint): mean |dlogit| of medians v2->v3 is 0.077,
max 0.54 (Chapter 1: 14.93 -> 23.15; Baited My Tackle: 13.86 -> 21.49;
Trust: 6.61 -> 10.25). Median sums: v2 146.4, v3 170.3, live 157.9.
The change is small overall and moves exactly the trophies the live
page proves are still climbing. Downside if wrong is bounded (~0.05-0.08
mean logit on the moved trophies); upside if right is the same size
the other way. No fair trend-path backtest exists (the intermediate
reads between the refresh and the live page are not published, and
inventing them would be circular), so this rests on principle + the
live trajectory, stated honestly.

Re-verified after the change: p00/p01 valid (55 rows, non-decreasing,
in range), two runs byte-identical, runtime 0.051 s for both cases.
Live-page backtest unchanged at 2.1229 (flat path does not call
`_fit_earners`, as expected).

## 9. Improvement v4 (21 Nov ~18:05 WIB) — hoist timestamp parsing (speed)

Robustness test first: the real final case will carry ~300 reads (every
10 minutes for two days), but the entry had only ever run on 7-8 read
histories. A reconstructed final-like history (336 reads: launch-night
30-min reads, the 04:30 refresh rebuilt from the kit's stated sum,
log-interpolated 10-min reads to the live page at N~40,000) runs clean:
valid output, Chapter 1 median 25.75% (rising from 18.02% live, sane),
universal trophy tight at 99.95. But runtime was 0.123 s for that one
case — too close to the practice #1's 142 ms for comfort on a possibly
throttled grading server, and run_ms is the tie-break.

Change: log-time `x` per read is now computed once in `_forecast_case`
and passed to `_fit_players` / `_fit_earners`. Before, `_fit_earners`
re-parsed every read's timestamp for every trophy (55 x 336 parses).
Pure refactor, no math changed — PROVEN score-neutral: p00/p01 outputs
byte-identical to v3, and the 336-read output byte-identical to v3.

Result: 336-read case 0.123 s -> 0.077 s (-37%). p00/p01 still
~25 ms per case. Determinism holds (identical bytes across runs and
across the refactor).
