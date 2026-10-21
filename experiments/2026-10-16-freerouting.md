# Freerouting vs the in-house router

2026-10-16. Result: `router.engine: freerouting` exists, `internal` stays the
default.

**Question.** Would an established autorouter do better than the grid A*
router, especially on the dense 8x8 2020?

Setup: Specctra DSN/SES round trip, Freerouting run headless; template
copper locked, nets restricted to F.Cu, template inner-layer hops swapped for
via keep-outs (2.x refuses planes that carry traces) and restored after
import. Data-chain links it leaves open are finished in-house.

| board | engine | result |
|---|---|---|
| sq30-5050x16-p7.112, template | internal | DRC clean, 223 mm front track, 38 vias |
| sq30-5050x16-p7.112, template | Freerouting 1.5 | DRC clean after 1 link finished in-house; 265 mm, 35 vias |
| sq30-2020x64-p3.4, template | internal | DRC clean |
| sq30-2020x64-p3.4, template | Freerouting 1.5 | 6 links open, one boxed in: fails |
| sq30-5050x16-p7.112, template | Freerouting 2.5 | 13 power pads never reach a plane: fails |
| sq30-5050x16-p7.112, generated | internal | DRC clean, 209 mm front + 178 mm back, 47 vias, 31 s |
| sq30-5050x16-p7.112, generated | Freerouting 2.5 | 6 unconnected (power, port nets); 393 mm front track |
| sq30-2020x64-p3.4, generated | internal | fails (P4 has no path through 128 power vias) |
| sq30-2020x64-p3.4, generated | Freerouting 2.5 | 15 unrouted, finish step can't close D48->D49: fails |

Takeaways: on these boards the constraint is the data chain fencing the
front, which needs short In2 hops; Freerouting can't use In2 (KiCad exports
it as a plane) and 2.5 also struggles to fan power pads into planes. The
generated-back dense 8x8 was later solved by
[patterned power vias](2026-10-16-power-via-placement.md), not by the router.
