# SCC-203 Network Diagnostics and HTTP Proxy

Python networking coursework completed as part of the BSc Computer Science degree at Lancaster University.

This project explores how network applications communicate using sockets. It includes ICMP ping and traceroute implementations, alongside a multithreaded HTTP proxy with file-based caching. It provides academic examples of packet construction, hostname resolution, client-server communication and interpreting network responses.

## Features

| Component | What the code implements |
| --- | --- |
| ICMP ping | Builds echo requests, calculates checksums, parses reply headers and measures round-trip delay. |
| Traceroute | Sends ICMP or UDP probes with increasing time-to-live (TTL) values to discover intermediate hops. |
| HTTP proxy | Accepts TCP connections, handles clients in separate threads, retrieves origin-server responses and stores cached copies. |
| Command-line interface | Selects an application and accepts hostnames, ports, probe counts, timeouts and traceroute protocol options. |
| Web-server scaffold | Contains the coursework structure for a web server; request handling and the listening loop are not implemented. |

## Technical concepts

- **Networking:** IPv4, TCP, UDP, ICMP, HTTP, ports and hostname resolution.
- **Packet processing:** Binary headers, checksums, identifiers and TTL.
- **Diagnostics:** Round-trip timing, hop discovery and console output.
- **Concurrency:** A separate thread for each accepted proxy connection.
- **Storage:** Reading and writing cached HTTP responses on disk.

These are academic implementations intended to demonstrate networking concepts, rather than production support tools.

## Repository contents

| File or directory | Purpose |
| --- | --- |
| `NetworkApplications.py` | Main application, command-line parser and networking classes. |
| `TelnetWebSSH.imn` | Network topology configuration included with the coursework. |
| `index.html` | Small sample page for HTTP experiments. |
| `cache/` | Cached responses included in the repository; the proxy also writes responses here. |

## Requirements

- Python 3.
- No third-party Python packages: the application uses the standard library.
- An environment that permits raw ICMP sockets for ping and traceroute. On Linux, the examples below normally require elevated privileges.
- Run the proxy from a directory where it can create and write to `cache/`.

Raw-socket permissions and behaviour vary by operating system.

## Getting started

Clone the repository and view the available commands:

```bash
git clone https://github.com/shaj9054/SCC-203.git
cd SCC-203
python3 NetworkApplications.py --help
```

### Ping

Use an IPv4 address for the ping implementation:

```bash
sudo python3 NetworkApplications.py ping 127.0.0.1 --count 4 --timeout 2
```

The code constructs an ICMP echo request, receives a reply and prints its measured delay. The displayed packet length and TTL are hard-coded, rather than extracted from the reply.

### Traceroute

Examples for a local test environment:

```bash
sudo python3 NetworkApplications.py traceroute 127.0.0.1 --protocol icmp
sudo python3 NetworkApplications.py traceroute 127.0.0.1 --protocol udp
```

The implementation takes three measurements per hop and increases TTL up to 30 hops. It attempts reverse hostname resolution for responding addresses.

**Current limitation:** the parser accepts `--timeout`, but traceroute does not apply it to the receiving socket. A non-responsive hop can therefore cause the command to wait indefinitely. Use Ctrl+C to stop it.

### HTTP proxy

For a local demonstration, start a sample origin server in one terminal:

```bash
python3 -m http.server 8080 --bind 127.0.0.1
```

Start the coursework proxy in a second terminal:

```bash
python3 NetworkApplications.py proxy --port 8000
```

Then request the origin through the proxy in a third terminal:

```bash
curl --noproxy "" --proxy http://127.0.0.1:8000 http://127.0.0.1:8080/
```

The proxy stores the response in `cache/`. Repeating the request should use that cached response and print a cache message. Remove the corresponding cached file when you want to fetch a fresh response.

The proxy binds to all interfaces. Keep demonstrations within a local or isolated lab environment.

## Implementation limitations

- Ping prints a timeout message, but subsequent delay formatting does not handle the missing value and can raise an exception.
- Ping does not explicitly resolve hostnames; use an IPv4 address in its examples.
- Traceroute does not fully validate that received replies correspond to the probe sent.
- The proxy supports basic HTTP requests; HTTPS tunnelling through `CONNECT` is not implemented.
- Origin requests always fetch `/`, rather than preserving the requested path.
- Cache keys use the hostname, including an explicit port where supplied, rather than the full URL. Cache expiry and invalidation are not implemented.
- Proxy input validation, upstream timeouts and error handling are limited.
- The `web` command prints a startup message but does not serve requests.

## Possible improvements

Apply socket timeouts consistently, handle missing ping replies, validate ICMP responses, preserve HTTP request paths and improve cache keys and expiry. These would extend the coursework into a more reliable networking demonstration.

## Project context

**Author:** Mohammed Shajalal Sarwar  
**Module:** SCC-203  
**Language:** Python  
**Purpose:** University networking coursework
