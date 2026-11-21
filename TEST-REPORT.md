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
