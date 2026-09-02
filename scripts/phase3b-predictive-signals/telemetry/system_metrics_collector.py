#!/usr/bin/env python3
import time
import sys
import os
import argparse
import csv

def read_cpu():
    with open('/proc/stat', 'r') as f:
        line = f.readline()
    fields = [float(x) for x in line.split()[1:]]
    idle = fields[3] + fields[4] # idle + iowait
    total = sum(fields)
    return total, idle

def read_mem():
    mem = {}
    with open('/proc/meminfo', 'r') as f:
        for line in f:
            parts = line.split(':')
            if len(parts) == 2:
                key = parts[0].strip()
                val = int(parts[1].split()[0]) # kB
                mem[key] = val
    total_mb = mem.get('MemTotal', 0) / 1024.0
    free_mb = mem.get('MemFree', 0) / 1024.0
    avail_mb = mem.get('MemAvailable', free_mb) / 1024.0
    used_mb = total_mb - avail_mb
    return total_mb, used_mb, free_mb, avail_mb

def read_disk():
    # Sum read/write sectors across all physical block devices (sd*, nvme*, hd*)
    read_bytes = 0
    write_bytes = 0
    read_ios = 0
    write_ios = 0
    with open('/proc/diskstats', 'r') as f:
        for line in f:
            parts = line.split()
            if len(parts) >= 14:
                dev = parts[2]
                # Filter to main disk devices like sda, nvme0n1, etc.
                if dev.startswith('sd') or dev.startswith('nvme') or dev.startswith('vd'):
                    # To avoid double counting partitions (sda vs sda1), include only main devices or partition-less
                    if dev[-1].isdigit() and not dev.startswith('nvme'):
                        continue
                    read_ios += int(parts[3])
                    read_bytes += int(parts[5]) * 512
                    write_ios += int(parts[7])
                    write_bytes += int(parts[9]) * 512
    return read_bytes, write_bytes, read_ios, write_ios

def main():
    parser = argparse.ArgumentParser(description="System Metrics Collector")
    parser.add_argument("--output", required=True, help="Path to output CSV")
    parser.add_argument("--interval", type=float, default=1.0, help="Sampling interval in seconds")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    
    file_exists = os.path.exists(args.output) and os.path.getsize(args.output) > 0
    
    f = open(args.output, 'a', newline='')
    writer = csv.writer(f)
    
    if not file_exists:
        writer.writerow([
            "timestamp", "cpu_util_pct",
            "mem_total_mb", "mem_used_mb", "mem_avail_mb", "mem_used_pct",
            "disk_read_bytes_sec", "disk_write_bytes_sec", "disk_read_iops", "disk_write_iops"
        ])
        f.flush()

    prev_tot, prev_idle = read_cpu()
    prev_rbytes, prev_wbytes, prev_rios, prev_wios = read_disk()
    prev_time = time.time()

    try:
        while True:
            time.sleep(args.interval)
            now = time.time()
            dt = now - prev_time
            if dt <= 0:
                dt = 1.0

            tot, idle = read_cpu()
            rbytes, wbytes, rios, wios = read_disk()
            total_mb, used_mb, free_mb, avail_mb = read_mem()

            dtot = tot - prev_tot
            didle = idle - prev_idle
            cpu_util = (1.0 - (didle / dtot)) * 100.0 if dtot > 0 else 0.0

            r_sec = (rbytes - prev_rbytes) / dt
            w_sec = (wbytes - prev_wbytes) / dt
            rio_sec = (rios - prev_rios) / dt
            wio_sec = (wios - prev_wios) / dt

            mem_pct = (used_mb / total_mb * 100.0) if total_mb > 0 else 0.0

            writer.writerow([
                f"{now:.3f}", f"{cpu_util:.2f}",
                f"{total_mb:.1f}", f"{used_mb:.1f}", f"{avail_mb:.1f}", f"{mem_pct:.2f}",
                f"{r_sec:.0f}", f"{w_sec:.0f}", f"{rio_sec:.1f}", f"{wio_sec:.1f}"
            ])
            f.flush()

            prev_tot, prev_idle = tot, idle
            prev_rbytes, prev_wbytes, prev_rios, prev_wios = rbytes, wbytes, rios, wios
            prev_time = now

    except KeyboardInterrupt:
        pass
    finally:
        f.close()

if __name__ == "__main__":
    main()
