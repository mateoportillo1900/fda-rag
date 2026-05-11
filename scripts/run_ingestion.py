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
from pathlib import Path

import psycopg
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from fda_rag.ingestion.chunker import chunk_label
from fda_rag.ingestion.loader import embed_chunks, store_chunks
from fda_rag.ingestion.parser import parse_label


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--xml-dir",
        type=Path,
        default=Path("data/sample/xml"),
        help="Directory containing DailyMed XML files (default: data/sample/xml)",
    )
    args = parser.parse_args()

    xml_files = sorted(args.xml_dir.glob("*.xml"))
    if not xml_files:
        print(f"No XML files found in {args.xml_dir}")
        print("Run: uv run scripts/download_dailymed.py --sample")
        sys.exit(1)

    print(f"\nIngesting {len(xml_files)} file(s) from {args.xml_dir}\n")

    url = os.environ["DATABASE_URL"]
    total_chunks = 0
    failed: list[str] = []

    with psycopg.connect(url) as conn:
        for xml_path in xml_files:
            print(f"{xml_path.name}")
            try:
                label = parse_label(xml_path)
                chunks = chunk_label(label)

                if not chunks:
                    print("  no usable sections — skipping\n")
                    continue

                print(f"  {label.drug_name}: {len(label.sections)} sections -> {len(chunks)} chunks")
                embeddings = embed_chunks(chunks)
                stored = store_chunks(conn, chunks, embeddings)
                total_chunks += stored
                print(f"  stored {stored} rows\n")

            except Exception as exc:
                print(f"  ERROR: {exc}\n")
                failed.append(xml_path.name)

    print(f"Done. {total_chunks} chunks stored in Neon.")
    if failed:
        print(f"Failed files: {', '.join(failed)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
