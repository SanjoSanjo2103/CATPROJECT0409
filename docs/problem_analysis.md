# Problem Analysis — University Cloud Lab Idle Resource Cost

## 1. Context

A university operates cloud laboratories across multiple departments (Computer Science, Data Science) and semesters (Spring, Fall). Each course provisions cloud resources — VMs, GPU instances, storage volumes, Jupyter notebooks — for student labs, homework, and research.

## 2. The Core Problem

**Idle resources continue to generate cost because ownership is unclear.**

When a semester ends, nobody stops the resources. When a faculty member moves to another university, their provisioned resources become orphans. During semester breaks, resources sit idle for weeks. The result: the university pays for cloud capacity that nobody is using.

## 3. Root Cause Analysis

```
Why are idle resources not stopped?
  → Because nobody knows who owns them
    → Because there is no tagging/ownership system
      → Because provisioning was ad-hoc

Why do costs accumulate?
  → Because resources run 24/7 until manually stopped
    → Because there is no automated idle detection
      → Because IT doesn't have visibility into per-course usage

Why are manual audits ineffective?
  → Because they are infrequent (monthly at best)
    → Because checking each resource is time-consuming
      → Because there is no dashboard or automated tooling
```

## 4. Impact Assessment

### Financial Impact (Estimated for a mid-size university lab)
- **40 cloud resources** across 6 courses
- **Average monthly cost per resource**: $72 (VMs), $1,080 (GPUs), $14.40 (storage), $57.60 (notebooks)
- **Estimated 30-40% of resources idle** at any given time
- **Monthly waste**: $1,500 — $4,000 (depending on GPU count)
- **Annual waste**: $18,000 — $48,000

### Operational Impact
- IT team spends hours on manual cleanup
- Risk of deleting active workloads during bulk cleanup
- Faculty frustrated by unexpected resource termination
- No accountability or cost awareness per course

## 5. Stakeholder Analysis

| Stakeholder | Pain Point | Need |
|---|---|---|
| IT Admin | Manual audits, unclear ownership | Automated detection, clear ownership metadata |
| Faculty/Instructor | Resources stopped without warning | Notification, grace period, extension option |
| Department Head | Unexplained cloud bill increases | Cost reports, per-course attribution |
| Students | Lab environment unavailable when needed | Protection of active workloads |

## 6. Constraints

- Must run on **modest hardware** or free-tier cloud (no expensive monitoring tools)
- Must **augment** existing workflows, not replace them
- Must **not delete active workloads** — safety is paramount
- Must support at least **two organizational roles** with different permissions
- Rules must be **configurable**, not hard-coded
