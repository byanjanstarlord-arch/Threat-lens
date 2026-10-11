"""
ThreatLens AI - CLI Replay Engine Tool
python -m threatlens.replay [--speed 5.0] [--max-windows 50]
"""

import argparse
import time
from threatlens.backend.services.replay_service import replay_engine

def main():
    parser = argparse.ArgumentParser(description="ThreatLens AI Historical Dataset Replay Engine")
    parser.add_argument("--speed", type=float, default=1.0, help="Replay speed multiplier (e.g. 1.0, 5.0, 10.0)")
    parser.add_argument("--max-windows", type=int, default=50, help="Maximum number of windows to replay")
    args = parser.parse_args()

    print("=" * 60)
    print("THREATLENS AI - HISTORICAL DATASET REPLAY")
    print("Mode: Historical Dataset Replay (Zero Fake Telemetry)")
    print(f"Speed: {args.speed}x | Max Windows: {args.max_windows}")
    print("=" * 60)
    print(f"Total available test windows: {replay_engine.total_windows}")
    print(f"Streaming {args.max_windows} windows through production inference pipeline...\n")

    sleep_sec = max(0.01, 1.0 / max(0.1, args.speed))

    for i in range(args.max_windows):
        res = replay_engine.step_single_window()
        if res.get("status") == "COMPLETED":
            print("\nReplay reached end of test session partition.")
            break

        win_id = res.get("window_id")
        pred = res.get("prediction", {})
        fc = res.get("forecast", {})
        gt = res.get("actual_ground_truth", {})
        tr = res.get("traffic", {})

        print(f"[Window #{win_id:>4}] "
              f"Bytes: {tr.get('byte_rate', 0):>9.1f} B/s | "
              f"Pkts: {tr.get('packet_rate', 0):>6.1f} p/s | "
              f"Class: {pred.get('predicted_class', 'N/A'):<11} | "
              f"Conf: {pred.get('confidence', 0)*100:>5.1f}% | "
              f"Risk: {pred.get('risk_level', 'N/A'):<8} | "
              f"FC Prob: {fc.get('forecast_attack_probability', 0)*100:>5.1f}% | "
              f"GroundTruth: {str(gt.get('attack_occurred')):<5} "
              f"(Lead: {gt.get('lead_time_sec')}s)")

        time.sleep(sleep_sec)

    print("\n" + "=" * 60)
    print(f"Replay demonstration completed successfully ({args.max_windows} windows streamed).")
    print("=" * 60)

if __name__ == "__main__":
    main()
