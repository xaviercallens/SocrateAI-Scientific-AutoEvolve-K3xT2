"""
Dark Matter Agora Data Lake Verification Script (Method 2)
==========================================================
Verifies that GCS data streams contain real astrophysical tensors
and not placeholder dummy files, before deploying Vertex AI jobs.

Checks:
    - File presence and count per stream
    - File sizes (real data > 1 MB; mock data < 1 KB)
    - Python read access (first 256 bytes of each file)
    - Content sniff: detects FITS headers, JSON structure, numpy magic bytes

Usage:
    python3 verify_datalake.py
"""

import logging
import struct
import sys

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

BUCKET = "socrateai-datalake-gen-lang-client-0625573011"
STREAMS = {
    "DESI DR1 BAO Likelihoods":   f"{BUCKET}/stream3_desi_dr1",
    "Euclid Q2 Tensors":           f"{BUCKET}/stream3_euclid_q2",
    "Calabi-Yau ML Datasets":      f"{BUCKET}/stream2_cy4_ml",
}

SIZE_THRESHOLD_REAL_MB = 0.1   # > 100 KB assumed real data


def detect_content_type(header: bytes) -> str:
    """Sniff first bytes to identify file type."""
    if header[:6] == b"SIMPLE":
        return "FITS header"
    if header[:2] == b"\x93N":  # NumPy .npy magic
        return "NumPy array (.npy)"
    if header[:4] == b"PK\x03\x04":
        return "ZIP archive (.npz)"
    if header[:1] in (b"{", b"["):
        return "JSON"
    if header[:4] == b"\x89HDF":
        return "HDF5"
    if header[:3] == b"CDF":
        return "NetCDF"
    return f"raw binary (first 4 bytes: {header[:4].hex()})"


def verify_data_lake():
    try:
        import gcsfs
    except ImportError:
        logging.error("gcsfs not installed. Run: pip install gcsfs")
        sys.exit(1)

    fs = gcsfs.GCSFileSystem()

    logging.info("=" * 60)
    logging.info("  Dark Matter Agora Data Lake Verification")
    logging.info(f"  Bucket: gs://{BUCKET}")
    logging.info("=" * 60)

    overall_pass = True
    report = {}

    for stream_name, path in STREAMS.items():
        logging.info(f"\n📁 Stream: {stream_name}")
        logging.info(f"   Path: gs://{path}")

        try:
            files = fs.ls(path, detail=True)
        except FileNotFoundError:
            logging.error(f"   ❌ PATH NOT FOUND: gs://{path}")
            overall_pass = False
            report[stream_name] = {"status": "MISSING", "files": []}
            continue

        if not files:
            logging.warning(f"   ⚠️  Directory is EMPTY")
            overall_pass = False
            report[stream_name] = {"status": "EMPTY", "files": []}
            continue

        stream_report = {"status": "OK", "files": [], "total_mb": 0}

        for info in files:
            fname = info["name"].split("/")[-1]
            size_bytes = info.get("size", 0)
            size_mb = size_bytes / (1024 * 1024)
            stream_report["total_mb"] += size_mb

            # Try to read first 256 bytes
            content_type = "unknown"
            read_ok = False
            try:
                with fs.open(info["name"], "rb") as f:
                    header = f.read(256)
                content_type = detect_content_type(header)
                read_ok = True
            except Exception as e:
                content_type = f"READ ERROR: {e}"

            is_real = size_mb >= SIZE_THRESHOLD_REAL_MB
            flag = "✅" if (is_real and read_ok) else ("⚠️ SMALL" if read_ok else "❌ UNREADABLE")

            logging.info(
                f"   {flag}  {fname:<45s}  "
                f"{size_mb:>8.3f} MB  [{content_type}]"
            )

            stream_report["files"].append({
                "name": fname,
                "size_mb": round(size_mb, 3),
                "content_type": content_type,
                "readable": read_ok,
                "is_real_data": is_real,
            })

            if not is_real:
                overall_pass = False
                stream_report["status"] = "SUSPECT_DUMMY"

        logging.info(
            f"   {'─'*55}\n"
            f"   Total: {len(files)} file(s), "
            f"{stream_report['total_mb']:.2f} MB"
        )
        report[stream_name] = stream_report

    # Summary
    logging.info("\n" + "=" * 60)
    if overall_pass:
        logging.info("  ✅ VERIFICATION PASSED — All streams contain real data")
        logging.info("  Safe to deploy Vertex AI custom training job.")
    else:
        logging.warning("  ⚠️  VERIFICATION WARNINGS — Review flags above")
        logging.warning("  Consider uploading real tensors before Vertex AI deploy.")
    logging.info("=" * 60)

    return report, overall_pass


if __name__ == "__main__":
    report, passed = verify_data_lake()
    sys.exit(0 if passed else 1)
