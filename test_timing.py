import time
import os
import sys

# disable GCS to prevent resuming
os.environ['GCS_CHECKPOINT_URI'] = ''
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = ''

sys.path.append(os.path.abspath('src'))
from scripts.run_phase2_physical_k3_t2 import execute_phase2

# To bypass the resume, let's just monkeypatch the checkpoint loader
import src.alpha_evolve.coordinator
original_resume = src.alpha_evolve.coordinator.EvolutionCoordinator.resume_from_checkpoint
src.alpha_evolve.coordinator.EvolutionCoordinator.resume_from_checkpoint = lambda self: False

start = time.time()
execute_phase2(generations=2, pop_size=40)
elapsed = time.time() - start
print(f"Elapsed for 2 gens: {elapsed:.2f} seconds")
