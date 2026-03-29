# Architecture

## Purpose
Privacy Protocol Toolkit for P2P is a Python-based system for verifying privacy
properties over a real `py-libp2p` network. It combines:
- libp2p proof exchange over `/privacyzk/1.0.0`
- local SNARK verification for multiple privacy statements
- network-level privacy analysis and reporting
- optional verification-record pinning
- an optional local dashboard that orchestrates the existing CLI

The current implementation is a prototype and should not be treated as
production-hardened infrastructure.

## System Map
```
 ┌──────────────────┐
 │   demo-web        │
 │   dashboard       │
 │   (orchestrator)  │
 └────────┬─────────┘
          │
          ▼
 ┌──────────────────┐       ┌──────────────────┐
 │                   │──────▶│  privacyzk        │
 │                   │       │  protocol         │
 │                   │       │  network/privacyzk│
 │                   │       └────────┬─────────┘
 │      CLI          │                │
 │     cli.py        │                ▼
 │                   │       ┌──────────────────┐       ┌──────────────────┐
 │                   │──────▶│  SNARK layer      │──────▶│  Proof assets    │
 │                   │       │  privacy_protocol │       │  privacy_circuits│
 │                   │       └──────────────────┘       │  /params         │
 │                   │                                  └───────▲──────────┘
 │                   │       ┌──────────────────┐               │
 │                   │──────▶│  Analysis +       │       ┌──────┴───────────┐
 │                   │       │  Reporting        │       │  Verification    │
 │                   │       │  privacy_analyzer │       │  record pinning  │
 │                   │       │  report_generator │       │  filecoin_pin    │
 │                   │       └────────┬─────────┘       └──────────────────┘
 │                   │                │                         ▲
 │                   │                ▼                         │
 │                   │       ┌──────────────────┐              │
 │                   │       │  Reports +        │              │
 │                   │       │  artifacts        │              │
 │                   │       │  demo_reports/    │              │
 │                   │       └──────────────────┘              │
 │                   │─────────────────────────────────────────┘
 └──────────────────┘

 Edges:
   UI ──▶ CLI ──▶ privacyzk ──▶ SNARK ──▶ Assets
                                  ▲
   CLI ──▶ SNARK (direct)  ───────┘
   CLI ──▶ Analysis ──▶ Reports
   CLI ──▶ PIN ──▶ Assets
```

## Core Components

### CLI Surface
Entry point: `<repo-root>/libp2p_privacy_poc/cli.py`

The CLI is the main runtime surface. It exposes:
- `zk-serve`: serves proof requests for remote peers
- `zk-verify`: requests a statement proof from a remote peer and verifies it locally
- `analyze`: captures live network activity and, when configured, requests proof verification
- `zk-dial`: generates inbound traffic for analysis runs
- `pin-proof-record`: verifies local assets and stores a verification record
- `fetch-proof-record`: retrieves and optionally re-checks a stored verification record
- `demo-web`: starts a local dashboard that drives the CLI workflow

### Proof Exchange Layer
Path: `<repo-root>/libp2p_privacy_poc/network/privacyzk/`

This layer defines the `/privacyzk/1.0.0` request/response flow used between
peers. It handles:
- statement selection
- request/response encoding
- proof-serving integration
- local verification after exchange

### Privacy Protocol / SNARK Layer
Path: `<repo-root>/libp2p_privacy_poc/privacy_protocol/`

This layer contains the privacy statements and verification backends. In the
current flow, the main statements are:
- `membership`
- `continuity`
- `unlinkability`

Real proving assets are resolved from `privacy_circuits/params/...`, using the
canonical defaults documented in `docs/DEMO_CONTRACT.md`.

### Analysis + Reporting
Primary paths:
- `<repo-root>/libp2p_privacy_poc/privacy_analyzer.py`
- `<repo-root>/libp2p_privacy_poc/report_generator.py`
- `<repo-root>/libp2p_privacy_poc/metadata_collector.py`

This layer is separate from proof validity. It measures network behavior such
as peer count, connection patterns, and timing signals, then produces:
- console reports
- JSON reports
- reproducibility metadata
- proof exchange summaries
- actionable warnings

### Verification Record Pinning
Path: `<repo-root>/libp2p_privacy_poc/filecoin_pin/`

This layer creates compact verification records from local proof artifacts,
including statement metadata, hashes, verification result, and tool metadata.
It supports:
- pinning a record to an external pinning service
- fetching a record back by CID
- re-checking local assets against the fetched record

### Optional Dashboard
Path: `<repo-root>/libp2p_privacy_poc/demo_web/`

The dashboard is an orchestration layer, not a separate protocol
implementation. It starts and coordinates the existing CLI commands, captures
artifacts, and renders:
- proof status for all statements
- proof exchange timings
- network statistics and risk
- record pin/fetch results
- logs and output artifacts

## Runtime Workflow
```
 ┌─────────────┐
 │  zk-serve   │
 └──────┬──────┘
        ▼
 ┌─────────────────────────────────┐
 │  libp2p host listens on         │
 │  /privacyzk/1.0.0               │◄──────── proof exchange ─────────┐
 └─────────────────────────────────┘                                  │
                                                                      │
 ┌─────────────┐                    ┌─────────────┐                   │
 │  zk-dial    │                    │  analyze     │                  │
 └──────┬──────┘                    └──────┬──────┘                   │
        ▼                                  ▼                          │
 ┌──────────────────┐  peer    ┌──────────────────────┐               │
 │  generate inbound │ traffic │  analyzer connects    │───────────────┘
 │  peer traffic     │────────▶│  to proof server      │
 └──────────────────┘          └───┬──────────────┬───┘
                                   │              │
                                   ▼              ▼
                      ┌────────────────┐  ┌────────────────────┐
                      │ request proofs │  │ network observations│
                      │ membership     │  │ collected           │
                      │ continuity     │  └─────────┬──────────┘
                      │ unlinkability  │            │
                      └───────┬────────┘            ▼
                              │           ┌────────────────────┐
                              ▼           │ privacy risk       │
                      ┌───────────────┐   │ analysis           │
                      │ local proof   │   └─────────┬──────────┘
                      │ verification  │             │
                      └───────┬───────┘             │
                              ▼                     │
                      ┌───────────────┐             │
                      │ proof exchange│             │
                      │ summary       │             │
                      └───────┬───────┘             │
                              │                     │
                              ▼                     │
                      ┌───────────────┐◄────────────┘
                      │ report        │
                      │ generation    │
                      └───────────────┘

 ┌──────────────────┐      ┌──────────────────────────────┐
 │ pin-proof-record │─────▶│ verify local assets +        │
 └──────────────────┘      │ pin verification record      │
                           └──────────────┬───────────────┘
                                          ▼
                           ┌──────────────────────────────┐
                           │ fetch-proof-record +         │
                           │ optional recheck             │
                           └──────────────────────────────┘
```

### Proof-Serving Path
1. `zk-serve` starts a libp2p host and listens on a multiaddress.
2. A remote peer requests one of the supported privacy statements.
3. The server returns proof material and metadata for that statement.
4. The requesting side verifies the proof locally before accepting the result.

### Analysis Path
1. `analyze` starts its own libp2p host and optionally connects to a proof-serving peer.
2. `zk-dial` can generate additional inbound peers during the capture window.
3. The analyzer records peer activity, timing, and connection counts.
4. If `--zk-statement` is enabled, the analyzer requests proof verification from the target peer.
5. The report combines:
   - network privacy findings
   - proof verification results
   - reproducibility and artifact metadata

### Verification Record Path
1. `pin-proof-record` loads local proof assets for one or more statements.
2. The tool verifies those assets locally.
3. It builds a compact verification record and stores it through the configured pin backend.
4. `fetch-proof-record` retrieves the record by CID and can re-check local assets against it.

## Design Boundaries
- Proof validity and network privacy risk are intentionally separate concerns.
- The CLI is the source of truth; the dashboard wraps existing CLI behavior.
- Real proof mode is asset-driven and depends on the expected params layout.
- Pinning is additive and opt-in; existing proof flows do not depend on it.

## Important Runtime Data
- Proof assets: `<repo-root>/privacy_circuits/params/`
- Local demo/report artifacts: `<repo-root>/demo_reports/`
- Optional dashboard run artifacts: `<repo-root>/demo_reports/web/`

## Repository Map
- `<repo-root>/libp2p_privacy_poc/cli.py`: command entry point
- `<repo-root>/libp2p_privacy_poc/network/privacyzk/`: proof exchange protocol
- `<repo-root>/libp2p_privacy_poc/privacy_protocol/`: statement and SNARK logic
- `<repo-root>/libp2p_privacy_poc/filecoin_pin/`: verification-record pin/fetch flow
- `<repo-root>/libp2p_privacy_poc/demo_web/`: optional local orchestration dashboard
- `<repo-root>/docs/DEMO_CONTRACT.md`: canonical defaults and demo contract
