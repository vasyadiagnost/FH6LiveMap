# FH6 Live Map v0.9.22 — Meme Layer MVP

## Added

- Optional **Meme Co-Driver** sound layer in Settings.
- User sample folders on the PC:
  - `data/meme_layer/samples/collision/`
  - `data/meme_layer/samples/mega_fail_crash/`
  - `data/meme_layer/samples/jump_takeoff/`
- Phone browser streams audio samples from the PC over the local web server.
- Randomized shuffle-bag playback, so samples rotate without immediate boring repeats.
- Event detection in the phone UI from `/api/state` telemetry:
  - `collision`: sharp speed drop.
  - `mega_fail_crash`: speed was 120+ km/h and falls almost to zero.
  - `jump_takeoff`: sharp height / vertical speed increase.
- Settings controls:
  - Meme layer on/off.
  - Enable sound button for mobile browser autoplay rules.
  - Volume slider.
  - Rescan samples.
  - Test buttons for all three events.
- Server API:
  - `/api/meme/samples`
  - `/api/meme/rescan`
  - `/api/meme/sample/<event>/<filename>`

## Notes

- No copyrighted or built-in meme samples are included. Users drop their own local files into the sample folders.
- Empty sample folders are safe: the event is ignored instead of crashing the app.
- Thresholds can be edited in `data/meme_layer/config.json`.
