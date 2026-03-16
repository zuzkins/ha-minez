# AGENTS.md

## Project purpose
Build a Home Assistant custom integration, suitable for HACS distribution, that talks to a local Braiins/BOS+ API to:
- read miner status and performance metrics
- expose those values as Home Assistant entities
- send supported control commands to the miner

The implementation language is Python.

## Product constraints
- Must follow Home Assistant custom integration conventions.
- Must be installable as a HACS custom component.
- Prefer local-network communication only; assume miners are on the user's LAN.
- Do not depend on Home Assistant internals that are discouraged for custom integrations.
- Keep secrets out of logs and out of entity state attributes.

## Repository layout target
Use this structure unless there is a strong reason to change it:

```text
custom_components/
  minez/
    __init__.py
    manifest.json
    const.py
    config_flow.py
    coordinator.py
    api.py
    entity.py
    sensor.py
    switch.py
    button.py
    number.py
    diagnostics.py
    translations/
tests/
README.md
hacs.json
```

Add files only when they serve the integration cleanly.

## Integration design rules
- Use `DataUpdateCoordinator` for polling and shared state.
- Keep raw HTTP/API logic isolated in `api.py`.
- Normalize miner responses into typed Python models or well-structured dicts before entity code consumes them.
- Entity platforms should stay thin: presentation and service mapping only.
- Prefer explicit feature flags/capabilities discovered from the miner over hardcoded assumptions.
- Treat control operations separately from polling reads. Writes must have clear timeout and error handling.
- Assume miner firmware or API payloads may vary slightly by version; parse defensively.

## Home Assistant requirements
- Support UI setup via config flow from the start.
- Use `ConfigEntry` setup, not YAML-first design.
- Use stable unique IDs derived from miner identity.
- Provide diagnostics with sensitive values redacted.
- Raise Home Assistant exceptions appropriately (`ConfigEntryNotReady`, auth/connectivity errors, etc.).
- Prefer `aiohttp` and async I/O; do not block the event loop.
- Follow Home Assistant naming, entity category, device info, and translation conventions.

## HACS requirements
- Keep metadata complete enough for HACS consumption.
- Maintain a user-facing `README.md` with setup steps, supported entities, and limitations.
- Keep the integration self-contained under `custom_components/minez`.

## API expectations
- Base assumption: local Braiins/BOS+ HTTP API exposed by the miner.
- Before implementing endpoints, verify them against real miner payloads or the Braiins demo repository.
- Separate:
  - identity/info endpoints
  - telemetry/stats endpoints
  - control/action endpoints
- Preserve unknown fields in debug/diagnostic structures when useful, but do not surface noisy raw blobs as entity attributes.

## Quality bar
- Add tests for API parsing, coordinator updates, and config flow behavior.
- Prefer small, composable functions over large entity classes.
- Log enough to diagnose connectivity and parsing issues without leaking credentials or tokens.
- Fail closed on unsupported write actions rather than guessing.

## Decision defaults for future work
- Domain: `minez`
- Polling first, push later only if the miner API clearly supports it.
- Start with sensors for health/stats and add controls only after read paths are reliable.
- If there is a choice between broad abstraction and shipping a solid first miner model, prefer the solid first version with room to extend.

## Collaboration notes for the coding agent
- Read the current repository state before making structural decisions.
- If a real API sample is missing, create code seams that make payload adaptation easy later.
- When uncertain about Home Assistant specifics, prefer established HA integration patterns over custom framework code.
