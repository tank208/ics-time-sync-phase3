# PHASE 3 MASTER REFERENCE
## GPS/RTC Grandmaster Clock Validation on Raspberry Pi 5
**Researcher**: William Hall, DeVlieg Scholar / SURF Fellow — University of Idaho CIIR
**Sponsors**: NILE, Idaho Power Company
**Advisors**: Dr. John Shovic (PI) · Dr. Mary Everett (Co-Advisor)
**Last Updated**: 2026-07-22

> **Note on network details:** node IPs and SSH access patterns are
> omitted from this public document by design, given this project's own
> subject matter (OT/ICS Zero Trust security). Contact the researcher
> directly for lab-internal access details.

---

## 1. System Overview

| Node | Role | Reference | Notes |
|---|---|---|---|
| gm | Grandmaster clock | GPS/PPS via Uputronics HAT | Lab-resident, NILE-connected; source of primary validation dataset |
| fc | Field-portable grandmaster | GPS/PPS via Uputronics HAT | Battery + cellular hotspot; demonstrated live at ICUR 2026 |

**Core hardware:** Raspberry Pi 5, Uputronics GPS/RTC HAT (u-blox GPS
receiver, RV-3028 RTC), PPS on GPIO18 → chrony (stratum-1 reference) →
RTC holdover on GPS loss.

**Deviation from proposal:** DS3231 (proposed) → RV-3028 on the
Uputronics HAT (as-built, improvement). External TCXO (proposed) → cut
entirely; the HAT physically occupies the board space the TCXO needed
and the two are not concurrently installable in this configuration. Not
purchased. A frequency-reference decision for Phase 4 must resolve this
physical constraint, not just select a part.

---

## 2. Objectives vs. Results

| Proposed Objective | Result |
|---|---|
| GPS/RTC integration, <1 µs stability | **Achieved and exceeded** against the corrected ±1 µs benchmark: 0.2178 µs RMS steady-state grandmaster time inaccuracy, 4.6× margin, from a continuous soak of 37,158 samples. Reported as grandmaster time inaccuracy, not an end-device Category 3/4 compliance claim. |
| Allan Deviation, τ = 1s–10,000s | **Complete.** Near −1 slope (white phase modulation) across τ = 16s–10,000s. A soft spot at τ = 496–992s was root-caused to a NILE network segment conflict: the gm node's IP was reserved in the segment plan without a corresponding MAC/DHCP binding, so DHCP assigned that address to a different node, forcing a segment-level reset during the affected window. Network artifact, not an oscillator or PPS-discipline defect. |
| RTC holdover, <10 µs over 60 min | **Achieved analytically; the analytical result is itself the finding.** At the confirmed 8.05 ppm RTC drift rate (continuous-power measurement, Section 4), a 60-minute outage projects to ~29 ms — roughly four orders of magnitude beyond the original target. That target was never achievable with a bare commodity RTC crystal as the sole holdover reference; closing it requires a disciplined frequency reference (TCXO/OCXO class) — active Phase 4 decision. A separate 139.2-hour uncontrolled unpowered field event (Section 4) surfaced a second, more serious holdover failure mode not captured by crystal-drift analysis alone. |
| Reproducible, documented methodology | **In progress** — this repository update pass is that documentation. |

---

## 3. Steady-State Timing Performance

Primary validation dataset: gm node, 37,158 continuous samples.
**0.2178 µs RMS grandmaster time inaccuracy — 4.6× margin against the
corrected ±1 µs Annex A benchmark.** This is the ICUR poster's headline
figure.

A separate informal health check at the ICUR poster table (single
point-in-time reading, post 139.2-hour transport: PPS selected, reach
377, RMS offset 0.156 µs, stratum 1) confirmed the system was healthy on
arrival but is **not a substitute** for the validated 0.2178 µs figure
above — do not conflate the two.

## 4. GPS Denial, Holdover, and RTC Drift

**Indoor GPS-fallback (n = 5, warm reacquisition only):** PPS reach hit
zero at mean 207s (σ = 26s); offset at first reacquisition averaged
64 ms (σ = 20 ms, real and repeatable); reacquisition duration averaged
214s (σ = 13s). Antenna-disconnect-with-chronyd-alive only — does not
cover cold-boot recovery.

**Full-hour antenna-denial (three runs):** GPS SHM-refclock reach stayed
pinned at its locked value (octal 377) throughout every run — **not a
valid signal-loss indicator at any timescale tested.** Only PPS reach
dropping to zero reliably indicates denial. A secondary NTP source
(Cloudflare, `noselect`) showed offset swings of roughly −23 ms to
−102 ms within a single hour across all three runs, no consistent
periodicity, confirmed real via independent NTP cross-check —
**mechanism not yet identified.**

**RTC drift, continuous power (855/855 samples, zero gaps, 3-day
window):** **8.05 ppm**, RTC slow relative to system clock. This
supersedes an earlier informal −4.126 ppm baseline (pool-NTP conditions)
**in reliability, not as a revision of it** — read as a separate, more
tightly controlled measurement. Applies to short-duration outages under
continuous power only.

**Extended unpowered field event (139.2 hours / 5.8 days):** field unit
transported to/from ICUR powered off — ~10 hours at ~101°F (bus hold),
then ~129 hours at 70–78°F. Implied average drift: **19.39 ppm**, more
than double the continuous-power rate. Temperature was evaluated and
**ruled out arithmetically** (RV-3028 datasheet temp-vs-frequency curve
predicts ~−0.5 to −0.6 ppm for this outage — 30×+ too small, wrong order
of magnitude). Leading explanation: **supercapacitor voltage-sag on the
RTC backup** (RV-3028 status register 0x0E = 0x30: backup-switchover
flag set as expected, power-on-reset flag clear, suggesting the clock
likely continued running but possibly at degraded supply voltage). **This
is a leading hypothesis based on available register-level evidence, not
an independently confirmed root cause**, and the register bit-mapping
used has not been independently verified against the datasheet with full
confidence. Surfaced through real field use, not bench testing — directly
affects every field-portability claim this project makes.

## 5. Open Items

None of these change the validity of the Section 3 result.

* Thermal correlation with holdover: untested — no dedicated
  temperature sensor currently installed (blocked on hardware, not
  scheduling).
* Frequency correlation with holdover: not currently assessable — the
  only available signal during denial is chrony's own estimator, which
  is already known to degrade under denial (circular).
* Supercapacitor voltage-sag hypothesis (Section 4): leading hypothesis,
  not confirmed.
* 64 ms indoor-fallback reacquisition offset: not explained by crystal
  drift alone; likely PPS reacquisition transients, not isolated.
* Cloudflare offset swings during GPS denial: mechanism unidentified.
* Cost comparison (60×–107× vs. industrial units): receipt-verified BOM
  not yet finalized — do not cite either bound as final.

## 6. Known Tooling Defects

The project's automated analysis pipeline has a Stage 2 component with a
known schema defect (`gps_lock` / `pps_present` hardcoded null/false)
that produces incorrect non-compliance findings and should not be cited.
**Only Stage 1 structured JSON output is treated as reliable in this
repository.** Any Stage 2 prose output has been removed or corrected
before inclusion here.

## 7. Resolved (previously open, closed this phase)

* **ADEV soft spot, τ = 496–992s** — root-caused to a NILE network
  segment conflict (Section 2), not an oscillator or timing artifact.
  No longer requires cross-checking against an independent dataset.
* **Field-log gap** — resolved as an analysis-tooling artifact.

---

## References

[1] IEEE Standard C37.238-2017, "IEEE Standard Profile for Use of IEEE 1588 Precision Time Protocol in Power System Applications," IEEE, 2017.

[2] M. L. Psiaki and T. E. Humphreys, "GNSS Spoofing and Detection," Proceedings of the IEEE, vol. 104, no. 6, pp. 1258–1270, June 2016.

[3] J. Shovic et al., "NILE: Zero Trust Architecture for Critical Infrastructure Control Systems," University of Idaho CIIR, Technical Report CIIR-2024-03, 2024.

[4] W. Hall, Phase 1–3 Project Devlogs, University of Idaho NILE Project, 2026.

[5] D. W. Allan, "Statistics of Atomic Frequency Standards," Proceedings of the IEEE, vol. 54, no. 2, pp. 221–230, February 1966.

[6] R. Exel, "Clock Synchronization in IEEE 802.1 Time-Sensitive Networks," Proceedings of the IEEE International Symposium on Precision Clock Synchronization, 2018.
