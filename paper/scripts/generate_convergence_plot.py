import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import re
import numpy as np
import os

os.makedirs('paper/figures', exist_ok=True)

fig, ax = plt.subplots(figsize=(8, 4))
ax.set_yscale('log')
ax.set_xlabel('Generation', fontsize=12)
ax.set_ylabel(r'Best $\chi^2$', fontsize=12)
ax.set_title(r'$\chi^2$ Convergence — 300-Generation Extended Deep Burn', fontsize=13)
ax.axvline(75, color='gray', ls='--', alpha=0.5, label='Phase 2 end')
ax.axvline(150, color='gray', ls=':', alpha=0.5, label='Phase 4 end')

generations = []
best_chi2s = []
with open('outputs/local_deep_burn/extended_burn.log', 'r') as f:
    for line in f:
        match = re.search(r'Gen (\d+)/\d+.*?Best Chi2:\s*([\d.e+-]+)', line)
        if match:
            generations.append(int(match.group(1)))
            best_chi2s.append(float(match.group(2)))

ax.plot(generations, best_chi2s, color='blue', lw=2, label='Best $\chi^2$')
ax.legend()
plt.tight_layout()
fig.savefig('paper/figures/chi2_convergence.pdf', dpi=150)
