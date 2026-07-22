#!/usr/bin/env python3
"""
Phase 3 Log Analyzer
Stage 1: Python parser  -> exact metrics from chrony/iperf/offset logs
Stage 2: ics-timing-analyst-p3 -> publication-ready findings

Usage:
  python3 phase3_analyze.py --log <path> --type <type> --run <run>
"""

import argparse
import json
import sys
import os
import re
import math
from datetime import datetime
import ollama

OLLAMA_HOST   = "http://100.112.139.1:11434"
ANALYST_MODEL = "ics-timing-analyst-p3"

SPIKE_THRESHOLD_US     = 10.0
VIOLATION_THRESHOLD_US = 100.0
STEP_THRESHOLD_US      = 100.0


# ── PARSERS ──────────────────────────────────────────────────────────────────

def parse_chrony_tracking(content: str, run: str) -> dict:
    """
    Parse chrony tracking log (fixed-width, offset in seconds scientific notation).
    Columns: Date Time IP St Freq Skew Offset L Co OffsetSD RemCorr RootDelay RootDisp MaxErr
    """
    offsets_us = []
    spikes, violations, steps, anomalies = [], [], [], []
    timestamps, sources, strata = [], [], []
    prev_source = None

    for line in content.splitlines():
        # Skip headers and separators
        if not line.strip() or line.startswith("=") or "Date (UTC)" in line:
            continue
        parts = line.split()
        if len(parts) < 11:
            continue
        try:
            ts_str   = f"{parts[0]}T{parts[1]}Z"
            ip       = parts[2]
            stratum  = int(parts[3])
            offset_s = float(parts[6])   # seconds
            rem_corr = float(parts[10])  # seconds
        except (ValueError, IndexError):
            continue

        # Skip unsynchronized rows
        if ip == "0.0.0.0":
            continue

        offset_us = offset_s * 1_000_000
        offsets_us.append(offset_us)
        timestamps.append(ts_str)
        sources.append(ip)
        strata.append(stratum)

        # Source change detection
        if prev_source and ip != prev_source:
            anomalies.append(f"Reference source changed: {prev_source} -> {ip} at {ts_str}")
        prev_source = ip

        # Spike detection
        if abs(offset_us) > SPIKE_THRESHOLD_US:
            spikes.append({"timestamp": ts_str, "offset_us": round(offset_us, 4)})

        # Compliance violation
        if abs(offset_us) > VIOLATION_THRESHOLD_US:
            violations.append({"timestamp": ts_str, "offset_us": round(offset_us, 4)})

        # Clock step detection
        rem_corr_us = abs(rem_corr) * 1_000_000
        if rem_corr_us > STEP_THRESHOLD_US:
            steps.append({"timestamp": ts_str, "step_us": round(rem_corr_us, 4)})

    n = len(offsets_us)
    rms = round(math.sqrt(sum(x**2 for x in offsets_us) / n), 4) if n else None
    max_abs = round(max(abs(x) for x in offsets_us), 4) if n else None
    p95 = round(sorted([abs(x) for x in offsets_us])[int(0.95 * n)], 4) if n > 20 else None
    p99 = round(sorted([abs(x) for x in offsets_us])[int(0.99 * n)], 4) if n > 100 else None

    # Most common source and stratum
    ref = max(set(sources), key=sources.count) if sources else None
    st  = max(set(strata),  key=strata.count)  if strata  else None

    return {
        "log_type": "chrony",
        "run_phase": run,
        "parser": "python",
        "sample_count": n,
        "time_range": {
            "start": timestamps[0]  if timestamps else None,
            "end":   timestamps[-1] if timestamps else None
        },
        "rms_offset_us":  rms,
        "max_offset_us":  max_abs,
        "p95_offset_us":  p95,
        "p99_offset_us":  p99,
        "spike_count":    len(spikes),
        "violation_count": len(violations),
        "spikes":         spikes[:20],   # cap at 20 for analyst context
        "compliance_violations": violations,
        "clock_steps":    steps,
        "stratum":        st,
        "reference_source": ref,
        "gps_lock":       None,
        "pps_present":    False,
        "anomalies":      anomalies
    }


def parse_offset_csv(content: str, run: str) -> dict:
    """Parse offset CSV: timestamp,offset_us"""
    offsets_us, timestamps, spikes, violations = [], [], [], []
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "timestamp" in line.lower():
            continue
        parts = line.split(",")
        if len(parts) < 2:
            continue
        try:
            ts = parts[0].strip()
            offset_us = float(parts[1].strip())
        except ValueError:
            continue
        offsets_us.append(offset_us)
        timestamps.append(ts)
        if abs(offset_us) > SPIKE_THRESHOLD_US:
            spikes.append({"timestamp": ts, "offset_us": round(offset_us, 4)})
        if abs(offset_us) > VIOLATION_THRESHOLD_US:
            violations.append({"timestamp": ts, "offset_us": round(offset_us, 4)})

    n = len(offsets_us)
    rms = round(math.sqrt(sum(x**2 for x in offsets_us) / n), 4) if n else None
    max_abs = round(max(abs(x) for x in offsets_us), 4) if n else None

    return {
        "log_type": "offset_csv",
        "run_phase": run,
        "parser": "python",
        "sample_count": n,
        "time_range": {
            "start": timestamps[0]  if timestamps else None,
            "end":   timestamps[-1] if timestamps else None
        },
        "rms_offset_us":  rms,
        "max_offset_us":  max_abs,
        "spike_count":    len(spikes),
        "violation_count": len(violations),
        "spikes":         spikes[:20],
        "compliance_violations": violations,
        "clock_steps":    [],
        "gps_lock":       None,
        "pps_present":    False,
        "anomalies":      []
    }


def parse_iperf(content: str, run: str) -> dict:
    """Parse iperf3 text output for throughput, jitter, loss."""
    throughput_mbps, jitter_ms, loss_pct = [], [], []
    for line in content.splitlines():
        # TCP sender summary: look for Mbits/sec
        m = re.search(r'([\d.]+)\s+Mbits/sec', line)
        if m:
            throughput_mbps.append(float(m.group(1)))
        # UDP jitter
        m = re.search(r'([\d.]+)\s+ms\s+([\d]+)/([\d]+)', line)
        if m:
            jitter_ms.append(float(m.group(1)))
            lost = int(m.group(2))
            total = int(m.group(3))
            if total > 0:
                loss_pct.append(round(lost / total * 100, 4))

    return {
        "log_type": "iperf",
        "run_phase": run,
        "parser": "python",
        "avg_throughput_mbps": round(sum(throughput_mbps)/len(throughput_mbps), 2) if throughput_mbps else None,
        "max_throughput_mbps": round(max(throughput_mbps), 2) if throughput_mbps else None,
        "avg_jitter_ms":       round(sum(jitter_ms)/len(jitter_ms), 4) if jitter_ms else None,
        "avg_loss_pct":        round(sum(loss_pct)/len(loss_pct), 4) if loss_pct else None,
        "anomalies":           []
    }


PARSERS = {
    "chrony":     parse_chrony_tracking,
    "offset_csv": parse_offset_csv,
    "iperf":      parse_iperf,
}


# ── ANALYST ──────────────────────────────────────────────────────────────────

def analyze(client, metrics: dict, log_type: str, run: str) -> str:
    prompt = (
        f"Run: {run} | Log type: {log_type}\n\n"
        f"Computed metrics (Python-parsed, exact values):\n"
        f"{json.dumps(metrics, indent=2)}\n\n"
        "Provide publication-ready findings:\n"
        "1. IEEE C37.238 compliance status (COMPLIANT / NON-COMPLIANT)\n"
        "2. Key metrics: RMS offset, p95, p99, max spike, spike count, violation count\n"
        "3. GPS/PPS status if applicable\n"
        "4. Notable anomalies and probable causes\n"
        "5. Comparison to Phase 2 NILE NTP baseline (Pi-2 best run: 0.549 µs RMS, 48h)\n"
        "6. Recommended follow-up for next run"
    )
    resp = client.chat(
        model=ANALYST_MODEL,
        messages=[{"role": "user", "content": prompt}]
    )
    return resp["message"]["content"]


# ── MAIN ─────────────────────────────────────────────────────────────────────

def save_outputs(metrics: dict, findings: str, log_path: str, run: str):
    base = os.path.expanduser(f"~/Research/phase3_data/{run}")
    os.makedirs(base, exist_ok=True)
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    stem = os.path.splitext(os.path.basename(log_path))[0]
    metrics_out  = os.path.join(base, f"{stem}_{ts}_metrics.json")
    findings_out = os.path.join(base, f"{stem}_{ts}_findings.txt")
    with open(metrics_out, "w") as f:
        json.dump(metrics, f, indent=2)
    with open(findings_out, "w") as f:
        f.write(findings)
    print(f"\n  [saved] metrics  -> {metrics_out}")
    print(f"  [saved] findings -> {findings_out}")

def main():
    parser = argparse.ArgumentParser(description="Phase 3 Log Analyzer")
    parser.add_argument("--log",  required=True)
    parser.add_argument("--type", required=True,
                        choices=["chrony","offset_csv","iperf","ptp4l","phc2sys","gpsd"])
    parser.add_argument("--run",  required=True,
                        choices=["r1_baseline","r2_holdover","r3_saturation","r4_seven_day"])
    args = parser.parse_args()

    try:
        with open(args.log, "r") as f:
            content = f.read()
    except FileNotFoundError:
        print(f"ERROR: {args.log} not found", file=sys.stderr)
        sys.exit(1)

    if args.type not in PARSERS:
        print(f"ERROR: no Python parser for type '{args.type}' yet", file=sys.stderr)
        sys.exit(1)

    print(f"\n=== Phase 3 Analysis ===")
    print(f"Log:  {args.log}")
    print(f"Type: {args.type} | Run: {args.run}")
    print(f"Host: {OLLAMA_HOST}\n")

    print("[Stage 1] Parsing (Python)...")
    metrics = PARSERS[args.type](content, args.run)
    print(json.dumps(metrics, indent=2))

    print("\n[Stage 2] Analysis (ics-timing-analyst-p3)...")
    client   = ollama.Client(host=OLLAMA_HOST)
    findings = analyze(client, metrics, args.type, args.run)
    print(f"\n{findings}")

    save_outputs(metrics, findings, args.log, args.run)

if __name__ == "__main__":
    main()
