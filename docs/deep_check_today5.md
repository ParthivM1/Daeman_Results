# Deep Check Today5

Timestamp: 2026-02-26T16:16:57.198108+00:00

Cross-backend gate for automatic publish:
- upload_allowed: False

### ibm_marrakesh

- Slots: 6
- Wins vs X: 6/6 | mean dX=+0.331380
- Wins vs BB1: 6/6 | mean dBB1=+0.309245
- Wins vs XY4: 5/6 | mean dXY4=+0.046875
- Non-wins vs XY4:
  - q=8, t=6400dt, dXY4=-0.027344 (XY4)

- Pulse-level CONTOUR firing (applied_count / pulse_count_total / avg pulses per fired node):
  - q=6, t=6400dt: applied=6, pulses=28, avg=4.67, nodes=[0, 1, 2, 3, 4, 5]
  - q=6, t=8000dt: applied=6, pulses=24, avg=4.00, nodes=[0, 1, 2, 3, 4, 5]
  - q=8, t=6400dt: applied=8, pulses=38, avg=4.75, nodes=[0, 1, 2, 3, 4, 5, 6, 7]
  - q=8, t=8000dt: applied=8, pulses=34, avg=4.25, nodes=[0, 1, 2, 3, 4, 5, 6, 7]
  - q=12, t=6400dt: applied=12, pulses=62, avg=5.17, nodes=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
  - q=12, t=8000dt: applied=12, pulses=52, avg=4.33, nodes=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]

### ibm_torino

- Slots: 6
- Wins vs X: 6/6 | mean dX=+0.169271
- Wins vs BB1: 6/6 | mean dBB1=+0.100911
- Wins vs XY4: 5/6 | mean dXY4=+0.060547
- Non-wins vs XY4:
  - q=8, t=8000dt, dXY4=-0.027344 (XY4)

- Pulse-level CONTOUR firing (applied_count / pulse_count_total / avg pulses per fired node):
  - q=6, t=6400dt: applied=6, pulses=14, avg=2.33, nodes=[0, 1, 2, 3, 4, 5]
  - q=6, t=8000dt: applied=6, pulses=14, avg=2.33, nodes=[0, 1, 2, 3, 4, 5]
  - q=8, t=6400dt: applied=8, pulses=28, avg=3.50, nodes=[0, 1, 2, 3, 4, 5, 6, 7]
  - q=8, t=8000dt: applied=8, pulses=26, avg=3.25, nodes=[0, 1, 2, 3, 4, 5, 6, 7]
  - q=12, t=6400dt: applied=12, pulses=42, avg=3.50, nodes=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
  - q=12, t=8000dt: applied=12, pulses=38, avg=3.17, nodes=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]

## Source Files

- `data/validation3_marrakesh_deep_q6_today5.json`
- `data/validation3_marrakesh_deep_q8_today5.json`
- `data/validation3_marrakesh_deep_q12_today5.json`
- `data/validation3_torino_deep_q6_today5.json`
- `data/validation3_torino_deep_q8_today5.json`
- `data/validation3_torino_deep_q12_today5.json`
- `data/validation3_marrakesh_deep_aggregate_today5.json`
- `data/validation3_torino_deep_aggregate_today5.json`
- `data/validation3_cross_backend_deep_today5.json`