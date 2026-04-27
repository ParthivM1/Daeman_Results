# Daemon vs Fire Opal Matched Benchmark Snapshot

Compiled 2026-04-26.

This page summarizes the current live IBM / Q-CTRL Fire Opal comparison artifacts. These are benchmark-scoped results, not a universal SOTA claim. The strongest evidence is the completed matched matrix; the main remaining gap is repeatability across calibration windows, especially on Marrakesh.

## Completed Wins

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

## Repeatability Reruns

| Workload | Backend | Daemon / PQMCF best | Fire Opal best | Gap | Result |
| --- | --- | ---: | ---: | ---: | --- |
| TFIM mixed n16 v6 repeat | IBM Marrakesh | 0.882243 | 0.895440 | -0.013197 | Fire Opal win |
| XY ring n16 v12 repeat | IBM Marrakesh | 0.970332 | 0.975651 | -0.005319 | Fire Opal win |

## Interpretation

Daemon currently has strong matched-case wins over Fire Opal on several n16 IBM workloads, including best observed margins of +3.17%, +2.36%, and +1.04%. The evidence supports a serious technical review and larger validation push.

The defensible claim is: Daemon has demonstrated benchmark-scoped wins against Fire Opal on live IBM hardware, but stable cross-calibration SOTA is not yet proven. The next validation priority is repeated Kingston/Fez/Marrakesh runs, larger workloads, and third-party review.

## What Daemon Is Testing

Daemon is not only final histogram post-processing. The system combines:

- representation-aware circuit selection,
- TSME protection branches,
- CONTOUR drift control,
- transverse X/XX suppression,
- residual perturbation handling,
- backend-aware execution path selection,
- support/witness workflow and finalization.

## Artifact Boundary

The public repo is a benchmark/results showcase. Full compiler/runtime source, selector policy internals, calibration daemon code, and proprietary scheduling details are intentionally not included.
