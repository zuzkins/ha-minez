# MineZ Home Assistant Integration

Custom Home Assistant integration for Braiins OS+ miners exposed over the local gRPC API on port `50051`.

## Features
- UI config flow
- Local polling through Home Assistant
- Miner telemetry sensors
- Locate-device switch
- Pause, resume, restart, and reboot buttons
- Writable power target number when the miner exposes tuner constraints

## Current entity coverage
- Status and version sensors
- Hashrate, power, efficiency, temperature, share, uptime, and tuner-state sensors
- Locate-device switch
- Pause mining button
- Resume mining button
- Restart bosminer button
- Reboot miner button
- Power target number

## Requirements
- A miner running Braiins OS/BOS+ with the public gRPC API enabled
- Reachability from Home Assistant to `<miner-ip>:50051`
- Valid miner credentials

## Installation
1. Copy this repository into your Home Assistant `custom_components` path through HACS or manually.
2. Restart Home Assistant.
3. Add the `MineZ` integration from Settings > Devices & Services.
4. Enter the miner host, port, username, and password.

## Notes
- The integration vendors generated protobuf stubs from the public Braiins API definitions.
- This first version assumes insecure local gRPC, matching the public Braiins examples.
- API payloads may vary by firmware release, so some entities may be unavailable on specific miners.
