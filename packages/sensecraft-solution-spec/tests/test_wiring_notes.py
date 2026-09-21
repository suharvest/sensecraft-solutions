"""Wiring section: which images go to ``wiring.image`` and which stay in notes.

Only the first image is consumed as ``wiring.image``. A later standalone image
line belongs to the prose around it and must survive into ``wiring.notes``;
it used to be dropped because every image-only line was skipped.
"""

from sensecraft_solution_spec.markdown_parser import extract_wiring_for_lang

SECTION = """### Wiring

![Relay wiring](gallery/wiring.svg)

1. Connect SIG.
2. Connect VCC.

Soldered to the board - the pads are marked in the photo below.

![5 V and GND pads](gallery/pads.jpg)
"""


def test_first_image_becomes_wiring_image():
    image, _, _ = extract_wiring_for_lang(SECTION)
    assert image == "gallery/wiring.svg"


def test_first_image_is_not_repeated_in_notes():
    _, _, notes = extract_wiring_for_lang(SECTION)
    assert "gallery/wiring.svg" not in notes


def test_later_standalone_image_is_kept_in_notes():
    _, _, notes = extract_wiring_for_lang(SECTION)
    assert "![5 V and GND pads](gallery/pads.jpg)" in notes
    assert notes.index("pads are marked") < notes.index("gallery/pads.jpg")


def test_list_items_still_go_to_steps_not_notes():
    _, steps, notes = extract_wiring_for_lang(SECTION)
    assert steps == ["Connect SIG.", "Connect VCC."]
    assert "Connect SIG." not in notes
