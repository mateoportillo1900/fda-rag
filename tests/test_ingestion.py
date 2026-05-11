"""
Tests for the ingestion layer (parser + chunker).
These run without any API keys — no Voyage AI or database calls.
"""

from pathlib import Path

import pytest

from fda_rag.ingestion.chunker import CHUNK_SIZE, chunk_label
from fda_rag.ingestion.parser import SECTION_CODES, parse_label

SAMPLE_DIR = Path("data/sample/xml")
_has_samples = SAMPLE_DIR.exists() and any(SAMPLE_DIR.glob("*.xml"))


@pytest.mark.skipif(not _has_samples, reason="Sample XML files not present — run: uv run scripts/download_dailymed.py --sample")
class TestParser:
    def test_metformin_has_drug_name(self) -> None:
        label = parse_label(SAMPLE_DIR / "metformin.xml")
        assert "metformin" in label.drug_name.lower()

    def test_metformin_has_sections(self) -> None:
        label = parse_label(SAMPLE_DIR / "metformin.xml")
        assert len(label.sections) > 0

    def test_metformin_has_set_id(self) -> None:
        label = parse_label(SAMPLE_DIR / "metformin.xml")
        assert label.set_id != ""

    def test_all_samples_parse_without_error(self) -> None:
        for xml_file in sorted(SAMPLE_DIR.glob("*.xml")):
            label = parse_label(xml_file)
            assert label.drug_name, f"{xml_file.name}: missing drug name"
            assert label.set_id,    f"{xml_file.name}: missing set_id"

    def test_all_section_codes_are_known(self) -> None:
        for xml_file in sorted(SAMPLE_DIR.glob("*.xml")):
            label = parse_label(xml_file)
            for section in label.sections:
                assert section.code in SECTION_CODES, (
                    f"{xml_file.name}: unexpected section code {section.code!r}"
                )

    def test_warfarin_has_contraindications(self) -> None:
        label = parse_label(SAMPLE_DIR / "warfarin.xml")
        codes = {s.code for s in label.sections}
        assert "34070-3" in codes, "Expected CONTRAINDICATIONS section in warfarin label"


@pytest.mark.skipif(not _has_samples, reason="Sample XML files not present — run: uv run scripts/download_dailymed.py --sample")
class TestChunker:
    def test_chunks_respect_size_limit(self) -> None:
        label = parse_label(SAMPLE_DIR / "warfarin.xml")
        chunks = chunk_label(label)
        for chunk in chunks:
            # allow a small tolerance for the last window of each section
            assert len(chunk.chunk_text) <= CHUNK_SIZE + 50, (
                f"Chunk too large: {len(chunk.chunk_text)} chars"
            )

    def test_all_chunk_fields_populated(self) -> None:
        label = parse_label(SAMPLE_DIR / "metformin.xml")
        chunks = chunk_label(label)
        assert len(chunks) > 0
        for chunk in chunks:
            assert chunk.drug_name
            assert chunk.set_id
            assert chunk.section_code
            assert chunk.section_name
            assert chunk.chunk_text

    def test_long_section_gets_split(self) -> None:
        # Verify the sliding-window logic actually fires on a real long section.
        # At least one of our 10 sample labels must have a section > CHUNK_SIZE chars.
        found_split = False
        for xml_file in sorted(SAMPLE_DIR.glob("*.xml")):
            label = parse_label(xml_file)
            for section in label.sections:
                if len(section.text) > CHUNK_SIZE:
                    chunks = chunk_label(label)
                    section_chunks = [c for c in chunks if c.section_code == section.code]
                    assert len(section_chunks) > 1, (
                        f"{xml_file.name} section {section.code} is {len(section.text)} chars "
                        f"but only produced {len(section_chunks)} chunk(s)"
                    )
                    found_split = True
                    break
            if found_split:
                break
        assert found_split, "None of the sample labels had a section long enough to split — add a larger label"
