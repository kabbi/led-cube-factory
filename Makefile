# the-better-cube. `make all` regenerates and checks every board.
# Pick boards with BOARDS="sq30-5050x16-p7.112-tpl sq30-2020x64-p3.4-tpl".
KICAD_PY ?= /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
PY := .venv/bin/python
TBC := $(PY) -m tbcgen
BOARDS ?=
SHAPES ?=
PANELS ?=

.PHONY: setup build check render fab all panel release model shapes docs test clean

all:    ; $(TBC) all $(BOARDS) && $(PY) -m pytest -q tests
build check render fab:
	$(TBC) $@ $(BOARDS)
# panels from panels/*.yaml (boards must be built); pick with PANELS="tri30-3535-15"
panel:  ; $(TBC) panel $(PANELS)
release:; $(TBC) release $(BOARDS)
model:  ; $(TBC) model $(BOARDS)
# demo polyhedra from shapes/*.yaml; pick with SHAPES="cube--sq30-2020x64-p3.4-tpl"
shapes: ; $(TBC) shapes $(SHAPES)
docs:   ; $(TBC) docs
test:   ; $(PY) -m pytest -q tests

setup:
	$(KICAD_PY) -m venv --system-site-packages .venv
	.venv/bin/pip install -q -r requirements.txt

clean:  ; rm -rf build
