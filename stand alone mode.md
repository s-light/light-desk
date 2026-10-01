# Stand Alone Mode

the light desk has two modes:

-   `control-desk`
-   `stand-alone`

## `control-desk`

in this mode the device has two functionalities:

-   sACN to DMX output on 4-6 universes
-   fader and button input to OSC output

## `stand-alone`

in this mode the desk does not need a computer connected.

the faders map in some ways to dmx output.

### Mode: `hsv-pixel-strip`

for the start i like to have just a simple script that does the following:
fader 0-2: HSV
fader 3: not used
fader 4: effect speed
fader 5: color-window wide
fader 6: master dimmer

the fader-backlight (universe 5) are used to visualize what the fader does.

buttons have no function for now.

the effect that is running: 1d _plasma_
effect → DMX: 1d 160 pixel RGB strip

### brainstorming

very nice would be to have a web-ui to configure the mapping.
some things that could be nice: define what fader has what functionality
but this could get very very complicated very quickly - so it does not make sens to do this all in software ourselfs..
maybe we could run a headless qlc+ to do all the havy lifting here..
this way we could to all the _hard work_ of defining and setting up all this on a pc and then _sync_ the showfile / config to the board..
