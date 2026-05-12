"""
Run the full ingestion pipeline against a directory of DailyMed XML files.

Steps:
    1. Parse each XML file into sections
    2. Chunk each section into overlapping text windows
    3. Embed each chunk with Voyage AI
    4. Store chunks + embeddings in Neon

Usage:
    uv run scripts/run_ingestion.py                          # data/sample/xml/ (default)
    uv run scripts/run_ingestion.py --xml-dir data/raw/xml   # full set
"""

import argparse
import os
import sys
import time
from pathlib import Path

import psycopg
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from fda_rag.ingestion.chunker import chunk_label
from fda_rag.ingestion.loader import embed_chunks, store_chunks
from fda_rag.ingestion.parser import parse_label

# Seconds to wait between files.
# Must be >= 60 so the previous file's tokens clear Voyage AI's 1-min TPM window.
INTER_FILE_SLEEP = 65


def ingest_one(xml_path: Path, url: str) -> int:
    """
    Parse, embed, and store a single XML file.
    Opens a fresh DB connection per file so Neon serverless idle-timeouts
    during INTER_FILE_SLEEP never kill an in-flight connection.
    Returns the number of chunks stored (0 if skipped).
    """
    label = parse_label(xml_path)
    chunks = chunk_label(label)

    if not chunks:
        print("  no usable sections — skipping\n")
        return 0

    print(f"  {label.drug_name}: {len(label.sections)} sections -> {len(chunks)} chunks")
    embeddings = embed_chunks(chunks)

    with psycopg.connect(url) as conn:
        stored = store_chunks(conn, chunks, embeddings)

    print(f"  stored {stored} rows\n")
    return stored


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--xml-dir",
        type=Path,
        default=Path("data/sample/xml"),
        help="Directory containing DailyMed XML files (default: data/sample/xml)",
    )
    parser.add_argument(
        "--drug",
        nargs="+",
        metavar="NAME",
        help="Ingest only these drug names (filename stems, e.g. --drug warfarin metformin)",
    )
    args = parser.parse_args()

    if args.drug:
        xml_files = sorted(
            args.xml_dir / f"{name}.xml"
            for name in args.drug
            if (args.xml_dir / f"{name}.xml").exists()
        )
    else:
        xml_files = sorted(args.xml_dir.glob("*.xml"))

    if not xml_files:
        print(f"No XML files found in {args.xml_dir}")
        sys.exit(1)

    print(f"\nIngesting {len(xml_files)} file(s) from {args.xml_dir}\n")

    url = os.environ["DATABASE_URL"]
    total_chunks = 0
    failed: list[str] = []

    for i, xml_path in enumerate(xml_files):
        print(f"{xml_path.name}")
        try:
            stored = ingest_one(xml_path, url)
            total_chunks += stored
        except Exception as exc:
            print(f"  ERROR: {exc}\n")
            failed.append(xml_path.name)

        # Wait between files: clears Voyage AI TPM window AND avoids RPM limit.
        # Skip the sleep after the last file.
        if i < len(xml_files) - 1:
            print(f"  [waiting {INTER_FILE_SLEEP}s before next file…]\n")
            time.sleep(INTER_FILE_SLEEP)

    print(f"Done. {total_chunks} chunks stored in Neon.")
    if failed:
        print(f"Failed files: {', '.join(failed)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
