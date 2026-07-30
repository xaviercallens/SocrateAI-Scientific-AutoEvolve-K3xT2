# MEMORY.md — SocrateAI Wolfram Hypergraph Session State & Recovery

**Last Updated:** 2026-07-28  
**Repository:** `SocrateAI-Wolfram-Hypergraph`  
**Status:** ✅ Fully Operational — 26/26 Tests Passing  
**Current Run:** Autonomous 1-hour batch simulation active (`task-132`) logging to `/mnt/disks/disk-socrateai-local-1/hypergraph_logs/batch_runs/`.

---

## 1. Quick Verification & Recovery Commands

To verify environment state or check batch simulation output:
```bash
# Check running batch simulation status
cat /mnt/disks/disk-socrateai-local-1/hypergraph_logs/batch_runs/batch_status.json

# Execute full unit test suite (26/26 passing)
cd /home/callensxavier_gmail_com/SocrateAI-Scientific-Agora-GraphDarkMatter/SocrateAI-Wolfram-Hypergraph
PYTHONPATH=. pytest --cov=hypergraph tests/
```

---

## 2. Directory & File Map

- `hypergraph/`
  - `phase0_tensor_masking.py`: Self-contained PyTorch Hadamard tensor masking MVP.
  - `cost_monitoring.py`: `GlobalCostMonitor` for burn rate tracking and < $100 budget cap.
  - `rate_limiter.py`: `WolframRateLimiter` token bucket throttler for Wolfram query endpoints.
  - `dry_run_local_mvp.py`: Local T4 + 500GB disk dry run benchmark script.
  - `batch_manager.py`: Timed batch manager for long-running hypergraph simulations.
  - `gpu_accelerated_engine.py`: PyTorch tensor-based hypergraph state evolution.
  - `oligon_simulations/`: Oligon topological defect simulations (`oligon_defect_sim.py`, `oligon_mfdm_mapper.py`).
  - `rewrite_rules/`: Multi-way Wolfram hypergraph rewriting rules (`rules.py`, `multiway_rules.py`).
- `specs/`
  - `system_specification.md`: Baseline hypergraph system specification.
  - `runux_ai_runtime_integration_v1_1.md`: Technical specification v1.2 including Phase 0 MVP.
  - `runux_integration_implementation_plan.md`: Actionable implementation plan v1.2 with DoD and validation criteria.
  - `deepmind_scientific_review_report.md`: Scientific review report for Google DeepMind / Deep Think.
- `deploy_gcp_phase0.sh` & `deploy_gcp_cost_optimized.sh`: GCP Spot VM provisioning scripts ($0.15/hr).

---

## 3. Latest Milestones Completed

1. **Phase 0 MVP Validated:** $M_{t+1} = (M_t^2 + M_t) \odot T$ keeps VRAM at $8.1\text{ MB}$ and edges at 40 (preventing exponential saturation).
2. **Global Cost & Rate Limiting Guardrails:** Burn rate ~$0.18/hr on Tesla T4; budget cap set to < $100. Token bucket rate limiter active.
3. **DeepMind Review Report Published:** [specs/deepmind_scientific_review_report.md](file:///home/callensxavier_gmail_com/SocrateAI-Scientific-Agora-GraphDarkMatter/SocrateAI-Wolfram-Hypergraph/specs/deepmind_scientific_review_report.md).
4. **Autonomous Batch Run:** `BatchManager` running in background on 500 GB storage mount (`task-132`).
