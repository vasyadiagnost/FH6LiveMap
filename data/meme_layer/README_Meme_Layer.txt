FH6 Live Map Meme Layer
=======================

Put custom sound samples on the PC here:
  data/meme_layer/samples/collision
  data/meme_layer/samples/mega_fail_crash
  data/meme_layer/samples/jump_takeoff

Supported formats: .mp3, .wav, .ogg, .m4a, .aac, .flac
Open the map on your phone, go to Settings, press 'Enable sound', and use Rescan after adding files.

Events:
  collision        - brake is not pressed, speed before hit was 60+ km/h, speed dropped by 40+ km/h in 0.5 s
  mega_fail_crash  - speed was 120+ km/h and fell to 15 km/h or lower in about 0.15 s
  jump_takeoff     - confirmed jump: recent ramp/upward impulse + fast freefall confirmation, about 0.15 s delay

Fullscreen:
  The old old screen-keepalive code was removed. The settings panel now has a lightweight Full screen mode button.
  Mobile browsers usually require a tap/click before fullscreen can be entered, so fully automatic fullscreen after QR scan is not reliable.
  If the phone still dims the display, set a longer screen timeout in Android/iOS settings.

v0.9.26 jump_takeoff note:
The jump trigger still uses the samples/jump_takeoff folder, but the detector no longer waits for about one second of falling.
It now confirms the jump shortly after the car starts falling, while still trying to ignore normal bridges/elevated roads.
