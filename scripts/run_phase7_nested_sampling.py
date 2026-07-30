import json
import os
import sys
import numpy as np
import dynesty
from dynesty import plotting as dyplot
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.mcmc.nested_sampler import NestedSamplingEngine

def run_lcdm_reference():
    print("Running LCDM Reference Evidence...")
    def log_likelihood(theta):
        h0 = theta[0]
        chi2 = ((h0 - 67.4) / 0.5) ** 2
        return -0.5 * chi2

    def prior_transform(u):
        return np.array([60.0 + u[0] * 20.0])

    sampler = dynesty.NestedSampler(
        log_likelihood, prior_transform,
        ndim=1, nlive=300, bound='single', sample='rwalk'
    )
    sampler.run_nested(dlogz=0.01, print_progress=True)
    res = sampler.results
    return {
        'logZ': float(res.logz[-1]),
        'logZ_err': float(res.logzerr[-1]),
        'n_params': 1
    }

def main():
    os.makedirs('outputs/nested_sampling', exist_ok=True)
    
    with open('outputs/pareto_frontier_final.json', 'r') as f:
        data = json.load(f)
        base_cand = data if 'geometry' not in data else data['geometry']
        
    print("Running K3xT2 Nested Sampling...")
    engine = NestedSamplingEngine(base_cand)
    results = engine.run(nlive=300, dlogz=0.01)
    k3t2_ev = engine.extract_evidence(results)
    k3t2_ev['n_params'] = 5
    
    lcdm_ev = run_lcdm_reference()
    
    ln_B10 = k3t2_ev['logZ'] - lcdm_ev['logZ']
    
    if ln_B10 > 5.0:
        verdict = "DECISIVE"
    elif ln_B10 > 2.5:
        verdict = "STRONG"
    elif ln_B10 > 1.0:
        verdict = "MODERATE"
    else:
        verdict = "INCONCLUSIVE"
        
    out_json = {
        "k3t2_model": k3t2_ev,
        "lcdm_model": lcdm_ev,
        "ln_bayes_factor": ln_B10,
        "jeffreys_verdict": verdict,
        "best_fit_params": {}
    }
    
    with open('outputs/nested_sampling/phase7_results.json', 'w') as f:
        json.dump(out_json, f, indent=2)
        
    # Corner plot
    param_names = ['tau', 'cs_1', 'cs_2', 'cs_3', 'picard_offset']
    fig, axes = dyplot.cornerplot(results, labels=param_names)
    fig.savefig('outputs/nested_sampling/corner_plot.png', dpi=150)
    print(f"Done. ln(B_10) = {ln_B10:.2f} ({verdict})")

if __name__ == "__main__":
    main()
