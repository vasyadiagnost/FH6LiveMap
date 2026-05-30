# FH6 Live Map v0.9.26 — Meme Layer fullscreen + faster jump trigger

## Changes

- Removed old screen-keepalive logic from the phone UI.
- Replaced the old old screen-keepalive button with a localized Full screen mode button.
- Fullscreen labels are included in RU/EN localization and update with the interface language.
- Retuned `jump_takeoff` to fire much sooner: confirmed freefall delay is now about 0.15 seconds instead of roughly one second.
- Updated meme layer config schema to v4; existing v0.9.25 configs migrate automatically.

## Notes

Mobile Chrome generally requires a user gesture before fullscreen can be entered, so the app uses an explicit Full screen mode button instead of trying to force fullscreen automatically after QR scan.
