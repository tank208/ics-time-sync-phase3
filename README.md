# ICS Time Synchronization on Commodity Hardware (Phase 3)

**GPS/RTC-disciplined Raspberry Pi 5 grandmaster clock, validated against
IEEE C37.238-2017 Annex A timing-accuracy budgets.**

This repository is the forward-facing, curated view of Phase 3 of an
ongoing OT/ICS timing-synchronization project, used for sponsors,
conference presentation, and independent replication. A separate private
lab repository holds full raw logs, devlogs, and scratch/in-progress
analysis scripts.

Phase 1/1.5 and Phase 2 (Raspberry Pi 4B, NTP/chrony over a NILE
Zero Trust network) are documented in a separate repository:
[`ics-time-sync-phase2`](https://github.com/tank208/ics-time-sync-phase2).

---

## Project context

Electrical grid protective relays require microsecond-precision timing to
coordinate protection across substations. GPS-dependent timing systems
that provide this precision are vulnerable to jamming, spoofing, and
signal denial, and purpose-built GPS-disciplined grandmaster clocks that
avoid this dependency carry costs that put them out of reach for smaller
utilities.

Phase 3 asks: can a Raspberry Pi 5 and a consumer-grade GPS/RTC HAT meet
the timing-accuracy component that IEEE C37.238-2017 substation timing
architectures require, at a small fraction of the cost of a purpose-built
industrial unit?

## Framing corrections (reported as findings, not errors)

Two corrections were made during Phase 3 execution. Both are documented
here directly rather than silently absorbed into later results, because
catching and reporting them is itself part of the validation process.

1. **Threshold.** Earlier project drafts benchmarked against <100 µs,
   drawn from IEC 61850-5 Type 2, the wrong standard. The applicable
   benchmark is **IEEE C37.238-2017, Annex A, Table A.1: ±1 µs**.
2. **Compliance scope.** The figures this project measures describe
   **grandmaster time inaccuracy**, a component of the total
   time-inaccuracy budget that downstream Category 3/4 end devices check
   against — not a direct end-device Category 3/4 compliance claim on
   its own.

## As-built system

The as-built hardware differs from the original proposal in two
respects: the RTC is the **RV-3028** on the Uputronics GPS/RTC HAT
(not a standalone DS3231 as originally specified), and the external TCXO
in the original proposal was cut entirely, the GPS/RTC HAT physically
occupies the board space the TCXO needed, and the two are not
concurrently installable in this configuration. The TCXO was not
purchased.

* Raspberry Pi 5, GPS-disciplined via Uputronics GPS/RTC HAT
  (u-blox GPS receiver, RV-3028 RTC)
* PPS signal on GPIO18 disciplining chrony as the stratum-1 reference
* chrony holdover to the onboard RTC on GPS signal loss
* Field-portable configuration ("fc"): battery power and cellular
  hotspot connectivity, demonstrated live at ICUR 2026
* Lab-resident grandmaster node ("gm") on a Zero Trust network,
  source of the primary validation dataset

## Headline result

Steady-state grandmaster time inaccuracy: **0.2178 µs RMS**, a **4.6×
margin** against the corrected ±1 µs Annex A benchmark, drawn from a
continuous soak dataset of **37,158 samples**.

Allan deviation across τ = 16s–10,000s shows a near −1 slope, consistent
with white phase modulation and a well-disciplined PPS reference.

Full methodology, statistical treatment, and open items are in
[`PHASE3_MASTER.md`](./PHASE3_MASTER.md).

## Status of open items

The following are reported as open, not resolved. None of them changes
the validity of the steady-state result above.

* Thermal correlation with holdover degradation: untested, blocked on a
  hardware gap (no dedicated temperature sensor currently installed),
  not a scheduling one.
* Frequency correlation with holdover degradation: not currently
  assessable without a reference independent of chrony's own estimator.
* A 139.2-hour uncontrolled unpowered field event implied 19.39 ppm RTC
  drift, roughly 2.4× the 8.05 ppm rate measured under continuous power.
  The leading explanation is supercapacitor voltage-sag on the RTC
  backup power, based on register-level evidence, **this is a leading
  hypothesis, not an independently confirmed root cause.**
* The 64 ms mean reacquisition offset seen in indoor GPS-fallback
  testing is not explained by crystal drift alone; most likely driven by
  PPS reacquisition transients, but this has not been isolated.
* Cost comparison against purpose-built industrial units: internal
  estimates range 60×–107× depending on reference unit and BOM
  methodology. **A receipt-verified, reconciled figure is not yet
  finalized** — treat the range as provisional.

See `PHASE3_MASTER.md` for full detail, including two items (an Allan
deviation soft spot and a field-log gap) that were investigated and
resolved to specific root causes.

## Repository contents

```
├── PHASE3_MASTER.md      # full technical reference and results
├── docs/
│   └── roadmap_phase4.md # direct follow-on work, not the full roadmap
├── scripts/              # analysis pipeline (Stage 1 output only — see PHASE3_MASTER.md)
└── results/
    └── examples/         # ICUR poster figures, ADEV plot
```

## Sponsors and acknowledgments

This work is supported by the University of Idaho Office of
Undergraduate Research (SURF Fellowship), NILE, and Idaho Power Company,
under the University of Idaho Center for Intelligent Industrial Robotics
(CIIR).

## License

MIT — see [LICENSE](./LICENSE).
