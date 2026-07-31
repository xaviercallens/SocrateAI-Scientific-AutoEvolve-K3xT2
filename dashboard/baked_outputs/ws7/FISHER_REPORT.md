# Fisher Information Matrix & Parameter Degeneracy Analysis (WS7)

**Date**: 2026-07-31  
**Workstream**: WS7 - Full 5D Fisher Information Matrix  
**Objective**: Compute the complete 5x5 FIM at the MAP point and analyze parameter degeneracies.

## Fisher Information Matrix

Evaluated at the MAP point:
- $\tau = 0.4998$
- $r_{cs} = 1.734$
- $\theta_{cs} = 0.994$
- $\phi_{cs} = -1.414$
- $\text{picard\_offset} = 0.0$

The numerical Fisher Information Matrix is:

```
[[ 391.73, -134.58,   0.0,   0.0,   0.0 ],
 [-134.58,   43.10,   0.0,   0.0,   0.0 ],
 [   0.0,      0.0,   0.0,   0.0,   0.0 ],
 [   0.0,      0.0,   0.0,   0.0,   0.0 ],
 [   0.0,      0.0,   0.0,   0.0,   0.0 ]]
```

## Parameter Degeneracy Analysis

1. **Singular FIM**: The Fisher Matrix is strictly singular. The sub-matrix for $(\theta_{cs}, \phi_{cs}, \text{picard\_offset})$ is identically zero.
2. **Angular Degeneracy**: The observables constrained by the current likelihood engine (DESI BAO distances and PTA monopole) depend only on the *magnitude* of the complex structure vector ($r_{cs}$) and the T² modulus ($\tau$). They do not depend on the angles $\theta_{cs}$ and $\phi_{cs}$. While `phenotype_mapper.py` introduced `pta_anisotropy`, `lya_spectral_tilt`, and `gw_polarisation` to break this degeneracy, the current likelihood evaluators do not include observational data to constrain these specific signatures. As a result, the angular components remain completely unconstrained (flat likelihood).
3. **Discrete Picard Number**: The `picard_offset` parameter is heavily quantized (rounded to the nearest integer before evaluating the `omega_m` mapping). Therefore, infinitesimal perturbations yield exactly zero gradient, leading to a zero Fisher matrix entry.
4. **tau / r_cs Correlation**: There is a strong correlation between $\tau$ and $r_{cs}$. $\tau$ controls $w_0$ and the PTA monopole frequency, while $r_{cs}$ controls $H_0$. Because both affect the expansion history measured by BAO, they share significant covariance.

## Conclusion

The 5D parameter space is fundamentally unidentifiable with the current observational probes. Genuine likelihood curvature analysis reveals that without adding concrete likelihood penalties for `pta_anisotropy` or `lya_spectral_tilt`, MCMC chains will fail to converge on the spherical angles, confirming the prior suspicion of parameter degeneracy.
