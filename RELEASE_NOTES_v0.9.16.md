# FH6 Live Map v0.9.16 — Retro VFD Dashboard HUD

## Added

- New **Dashboard / Приборы** mode with a clean black retro digital VFD-style screen.
- Dashboard can be opened from the mobile bottom dock or from Settings.
- Large live speed readout in km/h.
- Long RPM bar without numbers; red zone is the final part of the scale.
- RPM bar uses `EngineMaxRpm` from Forza telemetry when available, with a safe fallback.
- `TRIP A` now shows a live distance counter based on Forza `DistanceTraveled` telemetry.
- Left mini-navigation screen renders a live compact map view with route, player marker, destination, and POI dots.
- Tapping the mini-navigation screen returns to the main interactive map.

## Changed

- Telemetry API now exposes `engine_max_rpm` and `distance_traveled_m`.
- UI version bumped to `0.9.16-retro-vfd-dashboard`.

## Notes

- This is code-rendered UI, not static generated image assets.
- Existing map, navigator, POI, route, media, and language logic were preserved.
