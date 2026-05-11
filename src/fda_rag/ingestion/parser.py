"""Parse DailyMed SPL XML files into structured label objects."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

HL7_NS = "urn:hl7-org:v3"
_Q = f"{{{HL7_NS}}}"  # shorthand: _Q + "tag" == "{urn:hl7-org:v3}tag"

# LOINC codes for the sections we care about.
# Keys are the codes that appear in <code code="..."/> attributes.
SECTION_CODES: dict[str, str] = {
    "34067-9": "INDICATIONS AND USAGE",
    "34068-7": "DOSAGE AND ADMINISTRATION",
    "34070-3": "CONTRAINDICATIONS",
    "34071-1": "WARNINGS",
    "43685-7": "WARNINGS AND PRECAUTIONS",
    "34084-4": "ADVERSE REACTIONS",
    "34073-7": "DRUG INTERACTIONS",
    "34090-1": "CLINICAL PHARMACOLOGY",
}


@dataclass
class ParsedSection:
    code: str
    name: str
    text: str


@dataclass
class ParsedLabel:
    drug_name: str
    set_id: str
    sections: list[ParsedSection] = field(default_factory=list)


def _extract_text(element: ET.Element) -> str:
    """
    Pull all readable text out of an SPL <text> element.
    SPL text blocks contain <paragraph>, <list>, <item>, <content>, and
    raw text nodes — itertext() handles all of them in document order.
    """
    parts: list[str] = []
    for fragment in element.itertext():
        fragment = fragment.strip()
        if fragment:
            parts.append(fragment)
    return " ".join(parts)


def _get_drug_name(root: ET.Element, fallback: str) -> str:
    """
    Return the generic drug name from the SPL document.
    Looks for <genericMedicine><name> which holds the INN generic name.
    Falls back to the filename stem if not found.
    """
    elem = root.find(f".//{_Q}genericMedicine/{_Q}name")
    if elem is not None and elem.text:
        return elem.text.strip()
    # Secondary fallback: first <name> inside the product block
    elem = root.find(f".//{_Q}manufacturedProduct/{_Q}name")
    if elem is not None and elem.text:
        return elem.text.strip()
    return fallback


def _get_set_id(root: ET.Element) -> str:
    elem = root.find(f"{_Q}setId")
    return elem.get("root", "") if elem is not None else ""


def parse_label(path: Path) -> ParsedLabel:
    """
    Parse a DailyMed SPL XML file.
    Returns a ParsedLabel containing only the sections defined in SECTION_CODES.
    """
    tree = ET.parse(path)
    root = tree.getroot()

    label = ParsedLabel(
        drug_name=_get_drug_name(root, fallback=path.stem),
        set_id=_get_set_id(root),
    )

    for section in root.findall(f".//{_Q}section"):
        code_elem = section.find(f"{_Q}code")
        if code_elem is None:
            continue

        code = code_elem.get("code", "")
        if code not in SECTION_CODES:
            continue

        text_elem = section.find(f"{_Q}text")
        if text_elem is None:
            continue

        text = _extract_text(text_elem)
        if len(text) < 50:  # skip near-empty sections
            continue

        label.sections.append(
            ParsedSection(code=code, name=SECTION_CODES[code], text=text)
        )

    return label
