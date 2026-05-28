# FH6 Live Map v0.9.20 — HUD arrival fix and performance pass

## Fixed

- HUD navigation now automatically stops when the player reaches the destination.
- After arrival, HUD mini-map switches back to normal map mode and no longer tries to route the player back to the same target.
- Route state is cleared on arrival to prevent repeated rerouting to an already reached destination.

## Improved

- HUD rendering performance pass for mobile devices:
  - hidden main map DOM rendering is skipped while HUD mode is active;
  - dashboard speed / gear digits update only when values change;
  - RPM segment classes update only when the active segment count changes;
  - mobile HUD mini-map canvas uses a lighter DPR path;
  - mini-map redraw cadence is throttled separately from the main animation loop.

## Notes

- Main map, navigator, POI, routing, media controls, RU/EN UI and previous HUD layout are preserved.
