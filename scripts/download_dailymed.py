#!/usr/bin/env python3
"""
Download FDA drug-label XML files from the DailyMed public API.
No API key required. Politely rate-limited to 1 request/second.

Usage (from project root):
    uv run scripts/download_dailymed.py --sample          # 10 labels → data/sample/xml/  (commit these)
    uv run scripts/download_dailymed.py                   # 50 labels → data/raw/xml/     (gitignored)
    uv run scripts/download_dailymed.py --drug metformin warfarin  # specific drugs

The --sample set is small (~2-4 MB) and safe to commit to git.
The full set is ~25-40 MB and stays in data/raw/ (gitignored).
"""

import argparse
import sys
import time
from pathlib import Path

import httpx

BASE_URL = "https://dailymed.nlm.nih.gov/dailymed/services/v2"
HEADERS = {
    "Accept": "application/json",
    "User-Agent": "fda-rag-portfolio/0.1 (educational/non-commercial)",
}
RATE_LIMIT_SECONDS = 1.0

# ── 10-label sample: diverse therapeutic areas, interesting for RAG demos ──────
SAMPLE_DRUGS: list[str] = [
    "metformin",       # most prescribed diabetes drug; clean, readable label
    "warfarin",        # narrow therapeutic index; dense drug-interaction section
    "atorvastatin",    # common statin; good indications/contraindications
    "sertraline",      # SSRI; useful for mental-health queries
    "semaglutide",     # GLP-1 (Ozempic/Wegovy); high public interest
    "adalimumab",      # biologic (Humira); complex immunology label
    "amoxicillin",     # antibiotic; straightforward, good baseline
    "prednisone",      # corticosteroid; long warnings section
    "naloxone",        # opioid reversal agent; public-health relevance
    "pembrolizumab",   # immunotherapy (Keytruda); oncology use cases
]

# ── Full 50-label set: covers most major drug classes ──────────────────────────
ALL_DRUGS: list[str] = [
    # Top prescribed in the US
    "metformin", "atorvastatin", "levothyroxine", "lisinopril", "amlodipine",
    "omeprazole", "losartan", "albuterol", "gabapentin", "sertraline",
    "metoprolol", "simvastatin", "montelukast", "escitalopram", "rosuvastatin",
    # High-profile / high-interest
    "semaglutide", "adalimumab", "pembrolizumab", "apixaban", "rivaroxaban",
    # Complex safety profiles — great for testing retrieval accuracy
    "warfarin", "lithium", "digoxin", "phenytoin", "amiodarone",
    # Pain management
    "oxycodone", "hydrocodone", "tramadol", "buprenorphine", "naloxone",
    # Mental health
    "quetiapine", "aripiprazole", "bupropion", "duloxetine", "venlafaxine",
    # Antibiotics
    "amoxicillin", "azithromycin", "doxycycline", "ciprofloxacin", "levofloxacin",
    # Other important classes
    "prednisone", "insulin glargine", "sildenafil", "finasteride", "clonazepam",
    # Newer / notable
    "tirzepatide", "dupilumab", "paxlovid", "lecanemab", "ozanimod",
]


def search_set_id(client: httpx.Client, drug_name: str) -> str | None:
    """Return the DailyMed setId for the first matching label, or None if not found."""
    response = client.get(
        f"{BASE_URL}/spls.json",
        params={"drug_name": drug_name, "pagesize": 1},
    )
    response.raise_for_status()
    results = response.json().get("data", [])
    return results[0]["setid"] if results else None


def fetch_xml(client: httpx.Client, set_id: str) -> bytes:
    """Download the SPL XML document for the given setId."""
    response = client.get(f"{BASE_URL}/spls/{set_id}.xml")
    response.raise_for_status()
    return response.content


def download_one(client: httpx.Client, drug_name: str, out_dir: Path) -> bool:
    """
    Search for, download, and save one drug label XML.
    Skips the download if the file already exists (resumable).
    Returns True on success.
    """
    filename = drug_name.replace(" ", "_") + ".xml"
    dest = out_dir / filename

    if dest.exists():
        print(f"  skip   {drug_name:<22} (already exists)")
        return True

    set_id = search_set_id(client, drug_name)
    if set_id is None:
        print(f"  miss   {drug_name:<22} not found in DailyMed")
        return False

    time.sleep(RATE_LIMIT_SECONDS)  # be polite between the search and the download

    xml_bytes = fetch_xml(client, set_id)
    dest.write_bytes(xml_bytes)

    size_kb = len(xml_bytes) // 1024
    print(f"  ok     {drug_name:<22} {size_kb:>4} KB  ->  {dest}")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download DailyMed SPL XML files for a curated set of drug labels.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--sample",
        action="store_true",
        help="Download the 10-label sample set → data/sample/xml/ (safe to commit)",
    )
    group.add_argument(
        "--drug",
        nargs="+",
        metavar="NAME",
        help='Download specific drugs by name, e.g. --drug metformin "insulin glargine"',
    )
    args = parser.parse_args()

    if args.sample:
        drugs = SAMPLE_DRUGS
        out_dir = Path("data/sample/xml")
    elif args.drug:
        drugs = list(args.drug)
        out_dir = Path("data/raw/xml")
    else:
        drugs = ALL_DRUGS
        out_dir = Path("data/raw/xml")

    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"\nFetching {len(drugs)} label(s) from DailyMed -> {out_dir}\n")

    succeeded = failed = 0
    with httpx.Client(headers=HEADERS, timeout=30) as client:
        for drug in drugs:
            try:
                if download_one(client, drug, out_dir):
                    succeeded += 1
                else:
                    failed += 1
            except httpx.HTTPError as exc:
                print(f"  err    {drug:<22} HTTP error: {exc}")
                failed += 1
            time.sleep(RATE_LIMIT_SECONDS)

    print(f"\n  {succeeded} downloaded,  {failed} failed\n")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
