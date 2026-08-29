# FleetOpt Sensor-Free Predictive Maintenance Model Card

## Intended use
Research-MVP fleet maintenance prioritisation using vehicle usage, mileage,
maintenance history, service exposure, and structured driver inspections.

## Outputs
- calibrated 30-day unplanned-failure probability;
- calibrated next-2,000-km unplanned-failure probability;
- calibrated per-system risks for 14 maintenance systems;
- censored AFT planning estimates for days and kilometres to failure.

## Data
- training data version: `fleetopt-sensor-free-failure-v2`;
- validation scope: synthetic research MVP;
- sensor/diagnostic telemetry: not used;
- split: vehicle-disjoint train, calibration, threshold, and test groups.

## Operational boundary
The result is a planning aid, not a diagnosis or exact failure-date guarantee.
Critical actions must also consider inspections, open maintenance records,
manufacturer schedules, and qualified engineer review.

## Quality gate
Bundle pass: `True`.
See `metrics.json` and the included figures for complete evidence.
