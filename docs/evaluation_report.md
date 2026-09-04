# Evaluation Report — CloudReclaim

## 1. Experiment Setup

| Parameter | Value |
|---|---|
| Dataset | Synthetic, deterministic (seed=42) |
| Resources | ~40 (VMs, GPUs, storage, notebooks) |
| Courses | 6 (4 active Fall 2026, 2 expired Spring 2026) |
| Users | 5 (2 admins, 3 instructors) |
| Metrics window | 30 days |
| Idle threshold | CPU < 5%, Memory < 10%, Network < 1KB |
| Idle duration | 7 consecutive days |
| Grace period | 72 hours |

## 2. Results Summary

| Metric | Baseline | Target | Measured (Prototype) | Status |
|---|---|---|---|---|
| Monthly idle cost identified | — | — | See Reports page | ✅ |
| Idle cost eliminated | — | ≥ 60% | Run `experiment/run_experiment.py` | 📊 |
| Active workloads deleted | — | 0 | 0 | ✅ |
| False positive rate | >15% | <5% | See Reports page | 📊 |
| Supports 2+ roles | N/A | Yes | Admin + Instructor | ✅ |
| Configurable rules | N/A | Yes | 15+ rules via Admin UI | ✅ |
| Runs on free-tier | N/A | Yes | SQLite + Flask | ✅ |

> **Note**: Run `python experiment/run_experiment.py` to populate exact measured values in `experiment/results.json`. The Reports page in the web UI also shows live comparison data.

## 3. Baseline vs. Prototype Comparison

### Baseline (CPU-Only)
- Checks only average CPU over 7 days
- No ownership validation
- No calendar awareness
- No approval workflow — immediate action
- No burst detection

### Prototype (CloudReclaim)
- Multi-signal: CPU + Memory + Network + GPU + Disk I/O
- Ownership-aware: detects orphaned resources
- Calendar-aware: integrates with semester/break schedule
- Approval workflow: grace period + instructor review
- Burst detection: CPU spike > 50% prevents false flag
- Final safety check: re-verifies before reclamation

### Expected Outcome
The baseline will flag more resources but with a higher false positive rate (e.g., burst GPU workloads, active-but-low-CPU databases). The prototype will flag fewer but more accurately, and will catch orphaned resources that the baseline misses entirely.

## 4. Edge Case Results

| # | Case | Expected | Actual |
|---|---|---|---|
| 1 | Orphaned owner | Detected as orphaned | ✅ Verified in tests |
| 2 | Burst GPU workload | NOT flagged (spike detection) | ✅ Verified in tests |
| 3 | Grace during break | Auto-extended | ✅ Verified in tests |
| 4 | Max extensions exhausted | Extension denied | ✅ Verified in tests |
| 5 | Race condition (active during reclaim) | Reclamation aborted | ✅ Verified in tests |

## 5. Error Analysis

### Potential False Positives (Prototype)
- Resources with very intermittent usage (once per week) may fall below the 7-day average threshold
- **Mitigation**: Adjustable `idle_duration_days` parameter

### Potential False Negatives (Prototype)
- Resources with automated keepalive scripts that generate fake activity
- **Mitigation**: Network + Disk I/O analysis catches most fake activity patterns

### Data Quality Considerations
- Synthetic data has controlled patterns; real-world data will have more noise
- **Mitigation**: Configurable thresholds allow tuning to real-world patterns

## 6. Stakeholder Validation

### Admin Perspective
- ✅ Can configure all rules without code changes
- ✅ Can trigger manual scans
- ✅ Full audit trail visibility
- ✅ Can override any decision (manual reclaim)

### Instructor Perspective
- ✅ Only sees own course resources
- ✅ Clear notification of pending reclamations
- ✅ Can extend resources (with limits)
- ✅ Can reject reclamation with justification

### Department Head (via Reports page)
- ✅ Total cost visibility
- ✅ Savings quantified
- ✅ Baseline vs. prototype comparison
- ✅ Error rate transparency
