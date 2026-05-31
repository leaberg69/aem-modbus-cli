# aem-modbus-cli

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![pymodbus](https://img.shields.io/badge/pymodbus-3.x%20%7C%202.x-brightgreen)](https://github.com/pymodbus-dev/pymodbus)
[![Modbus](https://img.shields.io/badge/protocol-Modbus%20RTU%20%2F%20TCP-orange)](https://modbus.org/)
[![Companion](https://img.shields.io/badge/companion-aem--modbus--simulator-blue)](https://github.com/leaberg69/aem-modbus-simulator)

> Command-line diagnostic toolkit for Modbus RTU and TCP industrial deployments.

The five most common Modbus failure modes — termination issues, baudrate mismatches, slave ID conflicts, register addressing confusion, and silent CRC errors — are all things you should be able to diagnose **from your laptop** before you drive to site. This CLI gives you the primitives.

For the detailed field guide on those five mistakes, see this [Modbus debugging blog post](https://aem.lri.com.br/en-us/blog/post-01-guia-modbus-rtu).

## Subcommands

| Command | Purpose |
|---------|---------|
| scan | Discover Modbus slaves on a bus (sweep IDs 1-247) |
| baudrate | Probe a slave across all 6 standard baudrates to detect its rate |
| read | Read holding registers with retry, timing, and error diagnostics |
| bench | Measure RTT, CRC error rate, and effective throughput over time |

## Install

```bash
pip install pymodbus pyserial
```

## Usage examples

### Discover slaves on the bus

```bash
aem-modbus-cli --tcp 192.168.1.100:502 scan
aem-modbus-cli --port /dev/ttyUSB0 --baud 19200 scan --start-id 1 --end-id 50
```

### Detect baudrate when nobody documented it

```bash
aem-modbus-cli --port /dev/ttyUSB0 baudrate --slave-id 1
```

### Read with retry diagnostics

```bash
aem-modbus-cli --tcp 192.168.1.100:502 read --slave-id 1 --address 0 --count 8 --iterations 100 --interval 0.1
```

### Benchmark RTT and error rate

```bash
aem-modbus-cli --tcp 192.168.1.100:502 bench --slave-id 1 --duration 60
```

Reports total polls, success rate, RTT min/avg/p95/max, effective polls per second. Useful for confirming whether your supervisor polling rate is realistic given cellular RTT or RS-485 bus throughput limits.

## Why this exists

Most field Modbus issues come down to one of five common mistakes documented in this [Modbus debugging field guide](https://aem.lri.com.br/en-us/blog/post-01-guia-modbus-rtu). This toolkit lets you reproduce and rule out each of them without going to site.

For testing your CLI calls against a deterministic local target, see the companion **[aem-modbus-simulator](https://github.com/leaberg69/aem-modbus-simulator)** — open-source Python Modbus slave simulator that mirrors a real industrial DC monitor register map (147 holding registers).

## Companion projects

- [aem-modbus-simulator](https://github.com/leaberg69/aem-modbus-simulator) — Local Modbus slave for testing your master code
- [LRI AEM-60DC8](https://aem.lri.com.br/en-us) — Industrial DC voltage monitor (the hardware that motivated this toolkit)
- [Interactive Modbus map](https://aem.lri.com.br/en-us/modbus) — 147 holding registers documented
- [Technical whitepapers](https://aem.lri.com.br/en-us/whitepapers) — Secure by Design, IEC 62443-4-2 SL2, battery banks



## See also

- [awesome-industrial-modbus](https://github.com/leaberg69/awesome-industrial-modbus) — Curated list of all Modbus tools, libraries, simulators, and resources (lists this project alongside competing alternatives)
## License

MIT — see [LICENSE](LICENSE).

## Contributing

PRs welcome. Especially:

- Additional subcommands (write with verification, fuzz for malformed frames, mitm for transparent proxying)
- Output formats (JSON for CI integration, CSV for analysis)
- Integration tests against aem-modbus-simulator

## About

Built by [LRI Automação Industrial](https://lri.com.br), a Brazilian engineering firm focused on industrial DC monitoring, automation, and cybersecurity for critical infrastructure since 1995. Headquartered in Porto Alegre/RS with a branch in Navegantes/SC.
