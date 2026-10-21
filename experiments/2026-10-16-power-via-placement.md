# Power-via placement: nearest vs pattern

2026-10-16. Result: `router.power_vias: pattern` (`tbcgen/vias.py`), the
`pvia` name tag; `nearest` stays the default.

**Question.** Can the power vias be placed so they leave room for the data
chain and the back, instead of each one grabbing the closest free spot?

`pattern` reserves corridors for the data chain (in-row links + a return
band per row gap), then picks one LED-relative VDD/GND via offset that fits
the most LEDs against everything already on the board, and repeats it on
every LED; misfits get the nearest spot outside the corridors. On the 2020 it
chooses both vias under the LED body, between the pad columns.

| board | vias | result | front track | F.Cu segments | time |
|---|---|---|---|---|---|
| sq30-5050x16-p7.112, template | nearest | DRC clean | 222 mm | 142 | ~55 s |
| sq30-5050x16-p7.112, template | pattern | DRC clean (26/32 by pattern) | 241 mm | 111 | ~94 s |
| sq30-2020x64-p3.4, template | nearest | DRC clean | 439 mm | 556 | ~52 s |
| sq30-2020x64-p3.4, template | pattern | DRC clean (104/128 by pattern) | 452 mm | 438 | ~270 s |
| sq30-2020x64-p3.4, generated back | nearest | fails (P4 can't cross the back) | -- | -- | -- |
| sq30-2020x64-p3.4, generated back | pattern | **DRC clean**, 2.9 mm on In2 | 428 mm | 397 | ~260 s |

Patterned vias line up in columns on the back, which leaves channels for the
port/hub routing: the only way the dense board routes without a hand-drawn
template. On template boards the gain is mostly tidiness. Every generated
board since uses it, except where LEDs have mixed rotations
([LED rotation](2026-10-16-led-rotation.md)).

Pitfall: routing the chain ends before the data chain let a WS_OUT hop on In2
cut a +5V island off the plane (DRC: unconnected). In2 hops are cheap but
must not enclose plane areas.
