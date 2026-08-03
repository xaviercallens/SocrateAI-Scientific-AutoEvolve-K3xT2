import time
import os
import sys

# disable GCS to prevent resuming
os.environ['GCS_CHECKPOINT_URI'] = ''
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = ''

sys.path.append(os.path.abspath('src'))
from scripts.run_phase2_physical_k3_t2 import execute_phase2

# To bypass the resume, let's just monkeypatch the checkpoint loader
from utils.mlops_logger import EvolutionCheckpoint
EvolutionCheckpoint.load_latest_checkpoint = lambda self: None

start = time.time()
execute_phase2(generations=2, pop_size=40)
elapsed = time.time() - start
print(f"Elapsed for 2 gens: {elapsed:.2f} seconds")
