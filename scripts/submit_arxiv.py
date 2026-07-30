#!/usr/bin/env python3
"""
Simulate arXiv submission for Phase 6.
Packages the paper and figures into a tarball and mocks an API call.
"""

import tarfile
import os
import time
import json
from pathlib import Path

def main():
    print("=========================================")
    print("  Phase 6: arXiv Submission (Simulated)")
    print("=========================================")
    
    paper_dir = Path("paper")
    dist_dir = Path("dist")
    dist_dir.mkdir(exist_ok=True)
    
    tarball_name = dist_dir / "arxiv_submission.tar.gz"
    
    print(f"Packaging source files into {tarball_name}...")
    with tarfile.open(tarball_name, "w:gz") as tar:
        tar.add(paper_dir / "main.tex", arcname="main.tex")
        tar.add(paper_dir / "sections", arcname="sections")
        tar.add(paper_dir / "figures", arcname="figures")
        # include bbl file if exists (assuming it might be generated)
        
    print(f"Archive size: {os.path.getsize(tarball_name) / 1024:.2f} KB")
    print("Uploading to arXiv submission API endpoint (hep-th)...")
    
    # Simulate network latency
    time.sleep(2.0)
    
    # Mock arXiv response
    submission_id = "submit/5521092"
    arxiv_id = "2608.01945"
    
    response = {
        "status": "success",
        "submission_id": submission_id,
        "temporary_arxiv_id": arxiv_id,
        "category": "hep-th",
        "primary_cross_list": "astro-ph.CO",
        "message": "Submission accepted. Pending moderation."
    }
    
    print("\n✅ Submission Successful!")
    print(json.dumps(response, indent=2))
    
    # Save the submission receipt
    receipt_file = dist_dir / "arxiv_receipt.json"
    with open(receipt_file, "w") as f:
        json.dump(response, f, indent=2)
        
    print(f"\nReceipt saved to {receipt_file}")

if __name__ == "__main__":
    main()
