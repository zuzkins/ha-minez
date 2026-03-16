# memory.md

## Active project memory

### Goal
Create a Python Home Assistant custom component for HACS that integrates with local Braiins/BOS+ miners. The component should read miner statistics and expose safe control operations.

### Current assumptions
- Repository is starting from empty.
- Integration domain is `minez`.
- The miner is reachable on the local network over an HTTP-based Braiins/BOS+ API.
- The Braiins demo repository may be used later to validate endpoint names, payloads, and control semantics.

### Initial architecture direction
- Home Assistant custom integration under `custom_components/minez`.
- Async API client using `aiohttp`.
- Shared polling via `DataUpdateCoordinator`.
- Config flow for host/credentials and connection validation.
- Early entity focus:
  - miner status
  - hashrate
  - temperatures
  - fan speed
  - power-related metrics if available
- Control entities later, after API capabilities are confirmed:
  - restart/reboot button
  - expected-mode switch/select/number entities
  - other write actions only if clearly supported

### Important engineering constraints
- HACS-compatible repository shape and metadata.
- No blocking I/O in Home Assistant runtime code.
- Stable unique IDs per miner/device.
- Redact secrets in logs and diagnostics.
- Parse payloads defensively because firmware/API variants are likely.

### What to verify before implementing controls
- Authentication method, if any.
- Base URL and endpoint paths.
- Polling cost and acceptable refresh cadence.
- Which values are stable enough to expose as sensors.
- Which actions are actually safe/idempotent for Home Assistant use.

### Implementation priorities
1. Scaffold HACS + Home Assistant integration files.
2. Implement API client and typed normalization layer.
3. Implement config flow and coordinator.
4. Add read-only sensors.
5. Add diagnostics and tests.
6. Add carefully scoped control entities.
