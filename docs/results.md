# Results Summary (Torino)

Dataset:
- `data/torino/validation3_torino_full_q6_paritylift.json`
- `data/torino/validation3_torino_full_q8_paritylift.json`
- `data/torino/validation3_torino_full_q12_paritylift.json`
- `data/torino/validation3_torino_full_paritylift_aggregate_today.json`

Aggregate snapshot:
- Slots: 12
- Wins vs X: 12/12
- Wins vs BB1: 12/12
- Wins vs XY4: 11/12
- Mean dX: +0.1966
- Mean dBB1: +0.0833
- Mean dXY4: +0.0531
- Mean CONTOUR fidelity: 0.2669
- Mean no-drift ceiling: 0.2829
- Mean headroom: +0.0159

Interpretation:
- Deep windows (6400/8000dt) show strongest CONTOUR gains.
- Short-window losses are localized and small relative to deep-time advantage.
- Ceiling estimates indicate additional drift-limited headroom remains.

## Fire Opal Matched Benchmark Snapshot

Current live IBM / Q-CTRL Fire Opal comparison summary:

| Workload | Backend | Daemon / PQMCF best | Fire Opal best | Gap | Result |
| --- | --- | ---: | ---: | ---: | --- |
| TFIM mixed n16 v5 | IBM Marrakesh | 0.904184 | 0.872475 | +0.031709 | Daemon win |
| TFIM mixed n16 v4 | IBM Kingston | 0.921005 | 0.897435 | +0.023570 | Daemon win |
| TFIM mixed n16 v11 | IBM Fez | 0.917041 | 0.906602 | +0.010439 | Daemon win |
| Heisenberg mixed n16 v1 | IBM Marrakesh | 0.932244 | 0.923357 | +0.008887 | Daemon win |
| Heisenberg mixed n16 v2 | IBM Kingston | 0.929821 | 0.925930 | +0.003891 | Daemon win |
| XY ring n16 v1 | IBM Kingston | 0.971454 | 0.967945 | +0.003509 | Daemon win |
| XY ring n16 v8 | IBM Fez | 0.979066 | 0.975757 | +0.003309 | Daemon win |
| XY ring n16 v4 | IBM Marrakesh | 0.974682 | 0.972600 | +0.002082 | Daemon win |

Repeatability caveat:
- TFIM mixed n16 v6 repeat on IBM Marrakesh: Daemon 0.882243 vs Fire Opal 0.895440.
- XY ring n16 v12 repeat on IBM Marrakesh: Daemon 0.970332 vs Fire Opal 0.975651.

Current defensible claim: Daemon has benchmark-scoped live IBM wins against Fire Opal, but stable cross-calibration SOTA remains under validation.

Full table: `docs/fireopal_matched_results.md`
