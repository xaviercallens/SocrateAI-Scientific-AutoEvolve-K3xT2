🎯 Ordered Restart Plan — Follow This Exactly
The driver install is running right now. Here's what to do when it finishes:

✅ Step 1 — Let it finish
Don't interrupt the apt-get install nvidia-390 in your terminal. Wait for the prompt to return.

🔄 Step 2 — Clean reboot
bash
sudo reboot
⚡ Step 3 — After boot: verify GPU, then install deps
bash
# GPU alive?
nvidia-smi
# Swap (prevents OOM crashes during 24h run)
sudo fallocate -l 16G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile
# Missing Python deps
pip install gcsfs cobaya jax jaxlib scipy pandas psutil --break-system-packages
# GCS re-auth if needed
gcloud auth application-default login
🔬 Step 4 — 3-gen validation smoke test
bash
cd /home/xavkal/xdev/SocrateAI-Scientific-AutoEvolve-K3*T2
python3 -c "from scripts.run_phase2_physical_k3_t2 import execute_phase2; execute_phase2(generations=3, pop_size=5)"
🔥 Step 5 — Launch full 24h Deep Burn in tmux
bash
tmux new -s antigravity_burn
python3 scripts/run_local_deep_burn.py
# Ctrl+B, D  → detach safely
Everything needed is in 

docs/MEMORY.md
 in the repo — the complete project state is permanently recorded.