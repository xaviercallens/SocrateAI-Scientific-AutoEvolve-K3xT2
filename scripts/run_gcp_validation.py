import os
import sys
import time
import logging

# Bind exactly to local GPU
os.environ["CUDA_VISIBLE_DEVICES"] = "0"

# Ensure output directory exists
os.makedirs("./outputs/gcp_validation", exist_ok=True)

# Import existing Phase 2 logic
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.run_phase2_physical_k3_t2 import execute_phase2

# Configure logging to BOTH console and a persistent log file
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

file_handler = logging.FileHandler("./outputs/gcp_validation/validation_150.log")
file_handler.setFormatter(log_formatter)
root_logger.addHandler(file_handler)

if __name__ == "__main__":
    logging.info("==================================================")
    logging.info("🚀 INITIATING 150-GENERATION GCP VALIDATION RUN")
    logging.info("==================================================")
    
    start_time = time.time()
    try:
        # Exactly 150 generations, PopSize 40 (6,000 evaluations)
        execute_phase2(generations=150, pop_size=40)
    except Exception as e:
        logging.error(f"❌ FATAL ERROR: {e}")
        
    elapsed = (time.time() - start_time) / 3600
    logging.info("==================================================")
    logging.info(f"🏁 VALIDATION CONCLUDED. Total Runtime: {elapsed:.2f} Hours.")
    logging.info("==================================================")
