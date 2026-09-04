# Design Rationale — Why This Approach

## 1. Approach Comparison

We evaluated four approaches before choosing the current design:

| Approach | Description | Pros | Cons | Verdict |
|---|---|---|---|---|
| **A. Manual Audit** (current state) | Monthly spreadsheet review | No tooling needed | Slow, error-prone, no accountability | ❌ Status quo |
| **B. Simple Auto-Delete** | Delete anything with CPU < 5% | Fast to implement | High false positive rate, no safety | ❌ Too dangerous |
| **C. Cloud-Native Tools** (AWS Cost Explorer, GCP Recommender) | Use vendor monitoring | Battle-tested | Expensive, vendor lock-in, no academic calendar | ❌ Not free-tier |
| **D. Ownership-Aware Workflow** (chosen) | Multi-signal detection + calendar + approval | Safe, accurate, configurable | More complex to build | ✅ Best fit |

## 2. Why Multi-Signal Detection Over Single Metric

A CPU-only threshold (the baseline) fails for university workloads because:

1. **Database servers** have low CPU but high memory — flagged incorrectly
2. **GPU training jobs** run periodically with long idle gaps — flagged incorrectly
3. **Storage volumes** have near-zero CPU by nature — always flagged
4. **Jupyter notebooks** are idle between lab sessions but needed for the semester

Our multi-signal approach requires ALL metrics (CPU + Memory + Network + GPU) to be below thresholds simultaneously for a sustained period, dramatically reducing false positives.

## 3. Why Calendar Awareness Matters

University workloads follow academic rhythms:

- **During semester**: Resources should be protected even if temporarily idle
- **Between semesters**: Resources should be aggressively flagged
- **During breaks**: Grace periods should be extended (instructors can't respond)
- **During exams**: Lab resources may spike — don't flag during exam week

Without calendar awareness, a system would treat summer break resources the same as mid-semester resources, leading to either too many false positives or too many false negatives.

## 4. Why Approval Workflow Over Auto-Delete

Auto-deletion is faster but unsafe. The approval workflow provides:

1. **Notification**: Owner is informed before any action
2. **Grace period**: Time to respond (default: 72 hours)
3. **Extension option**: Legitimate resources can be extended (up to 2x)
4. **Snapshot safety**: Data is preserved before reclamation
5. **Audit trail**: Every decision is logged for accountability
6. **Final re-check**: If resource becomes active during grace period, reclamation is aborted

## 5. Why Flask + SQLite Over Heavier Stacks

| Decision | Rationale |
|---|---|
| **Flask** over Django | Lighter, faster to prototype, no ORM overhead for small models |
| **SQLite** over PostgreSQL | Zero configuration, runs anywhere, file-based, perfect for prototype |
| **Vanilla CSS** over Tailwind | No build step, full control over design system |
| **APScheduler** over Celery | In-process, no Redis/RabbitMQ dependency |
| **Chart.js** over D3.js | CDN-only, simpler API for dashboards |

All choices optimize for: runs on modest hardware, zero external dependencies, fast prototype iteration.

## 6. Why Configurable Rules

Hard-coding thresholds assumes one-size-fits-all. In practice:

- Different departments may have different idle thresholds
- GPU resources may need stricter policies than VMs
- Grace periods may need adjustment during exam seasons
- The university may want to tune over time based on experience

Exposing rules in the Admin UI lets operators adapt without code changes.

## 7. Trade-offs Acknowledged

| Trade-off | Chosen | Alternative | Why |
|---|---|---|---|
| Safety vs. Speed | Safety-first | Aggressive auto-delete | One wrongful deletion can destroy research data |
| Accuracy vs. Simplicity | Multi-signal | CPU-only | Academic workloads are too diverse for single-metric |
| Notifications | Simulated in UI | Real email/Slack | Prototype portability — no SMTP dependency |
| Authentication | Session-based | OAuth/SSO | Prototype simplicity — would integrate with university SSO in production |
