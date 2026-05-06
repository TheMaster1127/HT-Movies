"""
Estimate completion time for JSON pair generation, ignoring long pauses (gaps > 2 min).
Usage: python check_estimation.py [final_output_path] [target_pairs] [gap_threshold_seconds]
"""

import os
import sys
import time
import argparse
from pathlib import Path
from datetime import timedelta

def get_folder_start(folder_path):
    """Get folder creation time (birth if available, else modification time)."""
    stat = os.stat(folder_path)
    try:
        return stat.st_birthtime
    except AttributeError:
        return stat.st_ctime

def find_json_files(folder_path):
    """Return sorted list of modification times for all .json files recursively."""
    folder = Path(folder_path)
    json_files = list(folder.rglob("*.json"))
    times = [f.stat().st_mtime for f in json_files]
    times.sort()
    return times

def compute_active_time(file_times, gap_threshold):
    """
    Compute total active time (ignoring gaps > threshold).
    Returns: active_seconds, interval_count
    """
    if len(file_times) < 2:
        return 0.0, 0
    active = 0.0
    interval_count = 0
    for i in range(1, len(file_times)):
        gap = file_times[i] - file_times[i-1]
        if gap <= gap_threshold:
            active += gap
            interval_count += 1
    return active, interval_count

def format_time(seconds):
    """Convert seconds to D:H:M:S:MS string."""
    if seconds < 0:
        return "0 days, 0 hours, 0 minutes, 0 seconds, 000 milliseconds"
    millis = int((seconds % 1) * 1000)
    td = timedelta(seconds=int(seconds))
    days = td.days
    hours = td.seconds // 3600
    minutes = (td.seconds % 3600) // 60
    secs = td.seconds % 60
    return f"{days} days, {hours} hours, {minutes} minutes, {secs} seconds, {millis:03d} milliseconds"

def main():
    parser = argparse.ArgumentParser(
        description="Estimate time to reach target JSON pairs, ignoring long gaps (pauses)"
    )
    parser.add_argument(
        "folder",
        nargs="?",
        default="/home/themaster1127/GitHub_Projects/HT-Movies/raw_data/final_output",
        help="Path to final_output folder"
    )
    parser.add_argument(
        "--target-pairs", "-t",
        type=int,
        default=15111,
        help="Target number of JSON pairs (default 15111)"
    )
    parser.add_argument(
        "--gap-threshold", "-g",
        type=int,
        default=120,
        help="Gap threshold in seconds (default 120 = 2 minutes)"
    )
    args = parser.parse_args()

    folder = args.folder
    if not os.path.isdir(folder):
        print(f"Error: Folder not found: {folder}", file=sys.stderr)
        sys.exit(1)

    folder_start = get_folder_start(folder)
    folder_age = time.time() - folder_start

    json_times = find_json_files(folder)
    json_count = len(json_times)
    current_pairs = json_count // 2

    if json_count == 0:
        print("No JSON files found. Cannot estimate.")
        sys.exit(0)

    active_time, interval_count = compute_active_time(json_times, args.gap_threshold)

    if active_time <= 0 or current_pairs == 0:
        print("Insufficient active time or no pairs yet. Cannot estimate rate.")
        sys.exit(0)

    rate_pairs_per_sec = current_pairs / active_time
    rate_pairs_per_min = rate_pairs_per_sec * 60
    rate_pairs_per_hour = rate_pairs_per_sec * 3600

    # Average time per JSON file (seconds)
    avg_sec_per_json = active_time / json_count
    # Average time per pair (seconds)
    avg_sec_per_pair = active_time / current_pairs

    if current_pairs >= args.target_pairs:
        print(f"Target already reached: {current_pairs} pairs (>= {args.target_pairs})")
        sys.exit(0)

    needed_pairs = args.target_pairs - current_pairs
    needed_sec = needed_pairs / rate_pairs_per_sec

    # Output
    print("=" * 70)
    print(f"Folder:                {folder}")
    print(f"Folder wall-clock age: {format_time(folder_age)}")
    print(f"JSON files found:      {json_count}")
    print(f"Current pairs:         {current_pairs}")
    print(f"Active creation time:   {format_time(active_time)}  (gaps > {args.gap_threshold}s excluded)")
    print(f"Creation rate:         {rate_pairs_per_sec:.4f} pairs/second")
    print()
    print("Additional statistics:")
    print(f"  Pairs per minute:    {rate_pairs_per_min:.2f}")
    print(f"  Pairs per hour:      {rate_pairs_per_hour:.2f}")
    print(f"  Seconds per pair of JSON:    {avg_sec_per_pair:.2f}")
    print()
    print(f"Target pairs:          {args.target_pairs}")
    print(f"Additional pairs needed: {needed_pairs}")
    print()
    print("Estimated time to reach target (active creation only):")
    print(f"  {format_time(needed_sec)}")
    print("=" * 70)

if __name__ == "__main__":
    main()
