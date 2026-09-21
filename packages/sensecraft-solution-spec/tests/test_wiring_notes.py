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


def test_indented_code_image_is_not_mistaken_for_the_wiring_image():
    # A 4-space-indented line is a code block; the AST does not count it as an
    # image, so wiring.image is a.png and a.png must not also appear in notes.
    content = "    ![code](code.png)\n\n![a](a.png)\n\n![b](b.png)\n"
    image, _, notes = extract_wiring_for_lang(content)
    assert image == "a.png"
    assert "a.png" not in notes
    assert "![b](b.png)" in notes
    assert "code.png" in notes


def test_inline_first_image_does_not_swallow_a_later_standalone_image():
    content = "See ![a](a.png) for the layout.\n\n![b](b.png)\n"
    image, _, notes = extract_wiring_for_lang(content)
    assert image == "a.png"
    assert "![b](b.png)" in notes


def test_non_ascii_filename_is_matched_after_url_normalisation():
    # The AST percent-encodes non-ASCII; the raw line does not.
    content = "![接线](gallery/接线图.png)\n\n1. Connect SIG.\n\n![焊盘](gallery/焊盘.jpg)\n"
    _, _, notes = extract_wiring_for_lang(content)
    assert "gallery/接线图.png" not in notes
    assert "![焊盘](gallery/焊盘.jpg)" in notes


def test_image_line_inside_a_fence_is_kept_verbatim():
    content = "![a](a.png)\n\n```\n![b](b.png)\n```\n"
    image, _, notes = extract_wiring_for_lang(content)
    assert image == "a.png"
    assert "![b](b.png)" in notes
