"""Part catalog sanity: pin maps must match KiCad's stock symbols.

This is the check that would have caught denser_v4 (5050 pinout on a 2020
footprint)."""
import os
import re
from pathlib import Path

import pytest

from tbcgen.config import LIB, load_parts

# KiCad's stock symbol library: $KICAD10_SYMBOL_DIR, else the usual install spots
KICAD_SYMBOLS = next((d / "LED.kicad_sym" for d in map(Path, filter(None, [
    os.environ.get("KICAD10_SYMBOL_DIR"),
    "/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols",
    "/usr/share/kicad/symbols", "/usr/local/share/kicad/symbols"]))
    if (d / "LED.kicad_sym").exists()), Path("LED.kicad_sym"))
ROLE = {"VDD": "VDD", "GND": "VSS", "DIN": "DIN", "DOUT": "DOUT"}
PARTS = load_parts()


def symbol_pins(name):
    s = KICAD_SYMBOLS.read_text()
    i = s.index(f'(symbol "{name}"')
    j = s.find('\n\t(symbol "', i + 10)
    return {num: pin for pin, num in
            re.findall(r'\(pin \w+ \w+.*?\(name "([^"]*)".*?\(number "([^"]*)"', s[i:j], re.S)}


@pytest.mark.skipif(not KICAD_SYMBOLS.exists(), reason="KiCad symbols not installed")
@pytest.mark.parametrize("name", PARTS["leds"])
def test_led_pinmap_matches_kicad_symbol(name):
    led = PARTS["leds"][name]
    pins = symbol_pins(led["kicad_symbol"])
    for role, num in led["pins"].items():
        assert pins[num] == ROLE[role], f"{name}: pad {num} is {pins[num]}, catalog says {role}"


@pytest.mark.parametrize("kind", ["leds", "capacitors"])
def test_footprints_exist(kind):
    for name, part in PARTS[kind].items():
        fp = LIB / "tbc.pretty" / f"{part['footprint']}.kicad_mod"
        assert fp.exists(), f"{name}: {fp} missing"
        pads = set(re.findall(r'\(pad "(\d+)"', fp.read_text()))
        assert set(part["pins"].values()) <= pads, f"{name}: pin map uses missing pads"
