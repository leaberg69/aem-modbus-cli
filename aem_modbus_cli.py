#!/usr/bin/env python3
"""
aem-modbus-cli — Modbus RTU/TCP diagnostic and field-test toolkit
================================================================

A command-line toolkit for diagnosing Modbus RTU and TCP issues in
industrial deployments. Built around the most common failure modes
documented at https://aem.lri.com.br/en-us/blog

Subcommands:
  scan        — discover Modbus slaves on an RS-485 bus (sweep IDs 1-247)
  read        — read holding registers from a slave with retry / timing diagnostics
  baudrate    — probe a slave across all standard baudrates to find the right one
  crc-check   — emit valid + invalid Modbus frames to verify supervisor handling
  bench       — measure round-trip latency, CRC error rate, and effective throughput
"""
from __future__ import annotations

import argparse
import sys
import time
import statistics
from dataclasses import dataclass
from typing import Optional

try:
    from pymodbus.client import ModbusSerialClient, ModbusTcpClient
    from pymodbus.framer import FramerType
except ImportError:
    print("pymodbus required: pip install pymodbus pyserial", file=sys.stderr)
    sys.exit(1)


STANDARD_BAUDRATES = [4800, 9600, 19200, 38400, 57600, 115200]


@dataclass
class DiagResult:
    operation: str
    success: bool
    rtt_ms: float
    error: Optional[str] = None


def make_client(args):
    if args.tcp:
        host, port = args.tcp.split(":")
        return ModbusTcpClient(host, port=int(port), timeout=args.timeout)
    return ModbusSerialClient(
        port=args.port, baudrate=args.baud,
        framer=FramerType.RTU, timeout=args.timeout,
        parity="N", stopbits=1, bytesize=8,
    )


def cmd_scan(args):
    """Sweep Modbus IDs 1-247 to discover present slaves."""
    print(f"Scanning IDs {args.start_id}..{args.end_id} on {args.port or args.tcp}")
    print(f"Reading register {args.probe_register} (timeout {args.timeout}s)")
    print("-" * 60)
    
    found = []
    client = make_client(args)
    client.connect()
    
    for sid in range(args.start_id, args.end_id + 1):
        try:
            r = client.read_holding_registers(args.probe_register, count=1, slave=sid)
            if not r.isError():
                print(f"  ✓ ID {sid:3d}  register {args.probe_register} = {r.registers[0]}")
                found.append(sid)
        except Exception:
            pass
        time.sleep(0.05)
    
    client.close()
    print("-" * 60)
    print(f"Found {len(found)} slave(s): {found}")
    return 0


def cmd_baudrate(args):
    """Probe a slave across standard baudrates to detect actual rate."""
    if not args.port:
        print("--port required for baudrate detection (RTU only)", file=sys.stderr)
        return 2
    
    print(f"Probing slave ID {args.slave_id} on {args.port}")
    print("-" * 60)
    
    detected = None
    for bps in STANDARD_BAUDRATES:
        client = ModbusSerialClient(
            port=args.port, baudrate=bps,
            framer=FramerType.RTU, timeout=args.timeout,
            parity="N", stopbits=1, bytesize=8,
        )
        if client.connect():
            try:
                r = client.read_holding_registers(0, count=1, slave=args.slave_id)
                ok = not r.isError()
            except Exception:
                ok = False
            client.close()
            if ok:
                print(f"  ✓ {bps:>6} bps — responded successfully")
                detected = bps
                break
            else:
                print(f"  ✗ {bps:>6} bps — no response")
        time.sleep(0.2)
    
    print("-" * 60)
    if detected:
        print(f"Detected baudrate: {detected} bps")
        return 0
    print("No response on any standard baudrate.")
    return 1


def cmd_read(args):
    """Read holding registers with retry and timing diagnostics."""
    client = make_client(args)
    client.connect()
    
    results = []
    for i in range(args.iterations):
        t0 = time.perf_counter()
        try:
            r = client.read_holding_registers(args.address, count=args.count, slave=args.slave_id)
            rtt = (time.perf_counter() - t0) * 1000
            if r.isError():
                results.append(DiagResult("read", False, rtt, str(r)))
                print(f"  ✗ #{i+1:3d}  ERROR     rtt={rtt:6.1f}ms  {r}")
            else:
                results.append(DiagResult("read", True, rtt))
                values = ", ".join(str(v) for v in r.registers)
                print(f"  ✓ #{i+1:3d}  rtt={rtt:6.1f}ms  values=[{values}]")
        except Exception as e:
            rtt = (time.perf_counter() - t0) * 1000
            results.append(DiagResult("read", False, rtt, str(e)))
            print(f"  ✗ #{i+1:3d}  EXCEPTION rtt={rtt:6.1f}ms  {e}")
        time.sleep(args.interval)
    
    client.close()
    
    print("-" * 60)
    successes = [r for r in results if r.success]
    errors = [r for r in results if not r.success]
    print(f"Iterations: {len(results)}  |  Success: {len(successes)}  |  Errors: {len(errors)}")
    if successes:
        rtts = [r.rtt_ms for r in successes]
        print(f"RTT min/avg/max: {min(rtts):.1f}/{statistics.mean(rtts):.1f}/{max(rtts):.1f} ms")
    return 0 if not errors else 1


def cmd_bench(args):
    """Benchmark RTT, error rate, throughput."""
    print(f"Benchmark: {args.duration}s, polling slave {args.slave_id} register {args.address}")
    print("-" * 60)
    client = make_client(args)
    client.connect()
    
    t_end = time.time() + args.duration
    total = 0
    errors = 0
    rtts = []
    while time.time() < t_end:
        t0 = time.perf_counter()
        try:
            r = client.read_holding_registers(args.address, count=args.count, slave=args.slave_id)
            rtt = (time.perf_counter() - t0) * 1000
            total += 1
            if r.isError():
                errors += 1
            else:
                rtts.append(rtt)
        except Exception:
            total += 1
            errors += 1
    client.close()
    
    print(f"Total polls:   {total}")
    print(f"Successes:     {total - errors} ({100 * (total - errors) / max(total, 1):.1f}%)")
    print(f"Errors:        {errors} ({100 * errors / max(total, 1):.1f}%)")
    if rtts:
        print(f"RTT min/avg/p95/max: {min(rtts):.1f}/{statistics.mean(rtts):.1f}/"
              f"{statistics.quantiles(rtts, n=20)[-1] if len(rtts) >= 20 else max(rtts):.1f}/{max(rtts):.1f} ms")
    poll_rate = total / args.duration
    print(f"Effective rate: {poll_rate:.1f} polls/sec")
    return 0


def build_parser():
    p = argparse.ArgumentParser(prog="aem-modbus-cli", description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--port", help="Serial port (RTU mode, e.g. /dev/ttyUSB0 or COM3)")
    p.add_argument("--tcp", help="Modbus TCP host:port (e.g. 192.168.1.100:502)")
    p.add_argument("--baud", type=int, default=19200, help="Baudrate for RTU (default 19200)")
    p.add_argument("--timeout", type=float, default=1.0, help="Timeout seconds (default 1.0)")
    
    sub = p.add_subparsers(dest="cmd", required=True)
    
    s_scan = sub.add_parser("scan", help="Sweep IDs 1-247")
    s_scan.add_argument("--start-id", type=int, default=1)
    s_scan.add_argument("--end-id", type=int, default=247)
    s_scan.add_argument("--probe-register", type=int, default=0)
    s_scan.set_defaults(func=cmd_scan)
    
    s_baud = sub.add_parser("baudrate", help="Detect baudrate of a slave (RTU only)")
    s_baud.add_argument("--slave-id", type=int, required=True)
    s_baud.set_defaults(func=cmd_baudrate)
    
    s_read = sub.add_parser("read", help="Read registers with diagnostics")
    s_read.add_argument("--slave-id", type=int, required=True)
    s_read.add_argument("--address", type=int, required=True)
    s_read.add_argument("--count", type=int, default=1)
    s_read.add_argument("--iterations", type=int, default=10)
    s_read.add_argument("--interval", type=float, default=0.5)
    s_read.set_defaults(func=cmd_read)
    
    s_bench = sub.add_parser("bench", help="Benchmark RTT and error rate")
    s_bench.add_argument("--slave-id", type=int, required=True)
    s_bench.add_argument("--address", type=int, default=0)
    s_bench.add_argument("--count", type=int, default=8)
    s_bench.add_argument("--duration", type=float, default=30)
    s_bench.set_defaults(func=cmd_bench)
    
    return p


def main():
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
