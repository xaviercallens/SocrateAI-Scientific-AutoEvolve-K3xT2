"""
Script to validate all checkpoints in the datalake using Pydantic.
"""
import glob
import sys
import os

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from utils.data_validation import validate_checkpoint_file

def main():
    checkpoints = glob.glob("data/checkpoints/*.json")
    if not checkpoints:
        print("No checkpoints found.")
        return
        
    print(f"Found {len(checkpoints)} checkpoints to validate.")
    valid_count = 0
    error_count = 0
    
    for ckpt in checkpoints:
        try:
            validate_checkpoint_file(ckpt)
            valid_count += 1
        except Exception as e:
            print(f"❌ Validation failed for {ckpt}: {e}")
            error_count += 1
            
    print(f"Validation complete: {valid_count} valid, {error_count} failed.")

if __name__ == "__main__":
    main()
