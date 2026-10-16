"""Checksum generation and integrity verification for raw data assets."""
import hashlib
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional

from src.config import RAW_DIR
from src.utils import get_logger

logger = get_logger(__name__)


def sha256(path: Path, chunk_size: int = 1 << 20) -> str:
    """Compute the SHA-256 checksum of a file in streaming chunks."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while block := f.read(chunk_size):
            h.update(block)
    return h.hexdigest()


def write_manifest(folder: Path, source: str = "M5 Forecasting – Accuracy (Kaggle)") -> Path:
    """Scan folder for data files and generate a MANIFEST.md with sizes and SHA-256 hashes."""
    if not folder.exists():
        raise FileNotFoundError(f"Folder not found: {folder}")

    files = sorted([p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in [".csv", ".parquet"]])
    if not files:
        logger.warning(f"No .csv or .parquet files found in {folder} to generate manifest.")

    lines: List[str] = [
        f"# Manifest: {folder.name}",
        f"- Source: {source}",
        f"- Date: {date.today().isoformat()}",
        f"- Total Files: {len(files)}",
        "",
        "| File | Size (MB) | SHA-256 |",
        "|---|---:|---|",
    ]

    for p in files:
        size_mb = p.stat().st_size / 1e6
        chk = sha256(p)
        lines.append(f"| {p.name} | {size_mb:.2f} | `{chk}` |")
        logger.info(f"Hashed {p.name}: {size_mb:.2f} MB | {chk[:12]}...")

    manifest_path = folder / "MANIFEST.md"
    manifest_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"Wrote manifest with {len(files)} entries to: {manifest_path}")
    return manifest_path


def parse_manifest(manifest_path: Path) -> Dict[str, str]:
    """Parse an existing MANIFEST.md into a mapping of filename to SHA-256."""
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest file not found: {manifest_path}")

    hashes: Dict[str, str] = {}
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("|") and not line.startswith("| File") and not line.startswith("|---"):
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if len(parts) >= 3:
                filename = parts[0]
                checksum = parts[2].replace("`", "").strip()
                hashes[filename] = checksum
    return hashes


def verify_manifest(folder: Path) -> bool:
    """Verify all files listed in MANIFEST.md against their current disk contents."""
    manifest_path = folder / "MANIFEST.md"
    if not manifest_path.exists():
        logger.error(f"Cannot verify: MANIFEST.md does not exist in {folder}")
        return False

    recorded_hashes = parse_manifest(manifest_path)
    all_valid = True

    for filename, recorded_hash in recorded_hashes.items():
        file_path = folder / filename
        if not file_path.exists():
            logger.error(f"Missing file recorded in manifest: {filename}")
            all_valid = False
            continue

        current_hash = sha256(file_path)
        if current_hash != recorded_hash:
            logger.error(f"Integrity check failed for {filename}!")
            logger.error(f"  Expected: {recorded_hash}")
            logger.error(f"  Found:    {current_hash}")
            all_valid = False
        else:
            logger.info(f"Verified {filename}: OK")

    if all_valid:
        logger.info(f"All {len(recorded_hashes)} files in {folder.name} successfully verified!")
    return all_valid


if __name__ == "__main__":
    m5_folder = RAW_DIR / "m5_original"
    if m5_folder.exists() and any(m5_folder.glob("*.csv")):
        write_manifest(m5_folder)
        verify_manifest(m5_folder)
    else:
        logger.info(f"Folder {m5_folder} does not contain CSV files yet. Run download module first.")
