# Phase 4 Roadmap (direct follow-ons)

These are direct follow-ons from findings reported in Phase 3, not a
restatement of the full multi-phase project roadmap.

* **Thermal sensing.** Install a dedicated temperature-sensing module
  (e.g., DS18B20) on the field unit — prerequisite for thermal
  correlation and the next holdover run series. The Pi 5's own SoC
  sensor reads die temperature, not ambient or RTC-local temperature,
  and is not suitable for this correlation.
* **Frequency-reference hardware decision.** Resolve the physical space
  conflict between the RTC HAT and the originally proposed TCXO —
  evaluate a GPS-disciplined oscillator module against a waitlisted
  integrated timing HAT. This is a physical-integration decision, not
  just a component selection.
* **Supercapacitor voltage-sag characterization.** Fully characterize
  the failure mode identified in the 139.2-hour unpowered field event
  (see `PHASE3_MASTER.md`, Section 4) — determine whether it can be
  mitigated or must be designed around for extended unpowered transport.
* **White paper** for NILE project sponsors — the dissemination
  deliverable named in the original SURF proposal.
