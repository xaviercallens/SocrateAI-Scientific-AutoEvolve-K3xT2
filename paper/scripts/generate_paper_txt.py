#!/usr/bin/env python3
"""
generate_paper_txt.py — Assemble plain text version of paper/main.tex
"""

import os
import re

script_dir = os.path.dirname(os.path.abspath(__file__))
paper_dir = os.path.dirname(script_dir)
main_tex_path = os.path.join(paper_dir, "main.tex")
out_txt_path = os.path.join(paper_dir, "main.txt")

sections_order = [
    "01_introduction.tex",
    "02_autoevolve_approach.tex",
    "03_wolfram_hypergraph.tex",
    "03b_eft_bridge.tex",
    "04_results.tex",
    "05_dual_scale_alignment.tex",
    "06_reproducibility.tex",
    "07_conclusion.tex",
    "08_acknowledgments.tex"
]

header = """================================================================================
DUAL-TRACK CONVERGENCE IN COSMOLOGICAL DISCOVERY: ALIGNING MCMC EMPIRICAL EVOLUTION
WITH WOLFRAM HYPERGRAPH TOPOLOGICAL SIEVES ON K3 x T^2 MANIFOLDS
================================================================================

Author: Xavier Callens (Independent Researcher)
Date: July 30, 2026

ABSTRACT
--------------------------------------------------------------------------------
We derive the four-dimensional effective field theory emerging from Type IIA string
compactification on the Cooper s_10 K3 surface (rho = 19) fibred over T^2, and test
the resulting cosmological predictions against DESI DR1 baryon acoustic oscillation
data (12 measurements, full 12x12 covariance). The compactification yields a scalar
potential V(tau, phi) whose slow-roll dynamics predict w_0 = -0.974, Omega_m = 0.295,
H_0 = 69.3 km s^-1 Mpc^-1, and S_8 = 0.830, achieving a reduced goodness-of-fit
chi^2/dof = 12.7/7 = 1.81 against the DESI 2024 BAO distance ladder --- competitive with
the LambdaCDM baseline (chi^2/dof = 21.7/10 = 2.17). A Dynesty nested-sampling Bayesian
model comparison yields decisive evidence (ln B_10 = +13.60 +/- 0.09) under informed
priors from a 300-generation evolutionary landscape scan of 12,000 candidate geometries,
all verified by formal Lean 4 Swampland proofs (5 theorems, zero sorry axioms). The T^2
Compton scale predicts a gravitational-wave monopole at f = 1.07 x 10^-9 Hz with spectral
index gamma = 4.847, falsifiable by SKA-era pulsar timing arrays.

================================================================================
MANUSCRIPT SECTIONS
================================================================================
"""

def clean_latex(text):
    # Remove LaTeX commands for plain text readability
    text = re.sub(r'\\section\{([^}]+)\}', r'\n\n================================================================================\n\1\n================================================================================\n', text)
    text = re.sub(r'\\subsection\{([^}]+)\}', r'\n\n--------------------------------------------------------------------------------\n\1\n--------------------------------------------------------------------------------\n', text)
    text = re.sub(r'\\subsubsection\{([^}]+)\}', r'\n\n--- \1 ---\n', text)
    text = re.sub(r'\\paragraph\{([^}]+)\}', r'\n\n* \1: ', text)
    text = re.sub(r'\\cite\{([^}]+)\}', r'[\1]', text)
    text = re.sub(r'\\label\{([^}]+)\}', '', text)
    text = re.sub(r'\\ref\{([^}]+)\}', r'\1', text)
    text = re.sub(r'\\eqref\{([^}]+)\}', r'(\1)', text)
    text = re.sub(r'\\emph\{([^}]+)\}', r'_\1_', text)
    text = re.sub(r'\\textbf\{([^}]+)\}', r'**\1**', text)
    text = re.sub(r'\\texttt\{([^}]+)\}', r'`\1`', text)
    text = re.sub(r'\\mathrm\{([^}]+)\}', r'\1', text)
    text = re.sub(r'\\mathrm\s+', '', text)
    text = re.sub(r'\\operatorname\{([^}]+)\}', r'\1', text)
    text = re.sub(r'\\begin\{equation\}(.*?)\\end\{equation\}', r'\n[Equation: \1]\n', text, flags=re.DOTALL)
    text = re.sub(r'\\begin\{table\}.*?\\end\{table\}', r'\n[Table]\n', text, flags=re.DOTALL)
    text = re.sub(r'\\begin\{figure\}.*?\\end\{figure\}', r'\n[Figure]\n', text, flags=re.DOTALL)
    text = re.sub(r'\\begin\{enumerate\}', '', text)
    text = re.sub(r'\\end\{enumerate\}', '', text)
    text = re.sub(r'\\item\s+', '  * ', text)
    text = re.sub(r'\\%', '%', text)
    text = re.sub(r'\\sim', '~', text)
    text = re.sub(r'\\approx', '≈', text)
    text = re.sub(r'\\chi', 'chi', text)
    text = re.sub(r'\\Omega', 'Omega', text)
    text = re.sub(r'\\lambda', 'lambda', text)
    text = re.sub(r'\\tau', 'tau', text)
    text = re.sub(r'\\pi', 'pi', text)
    text = re.sub(r'\\alpha', 'alpha', text)
    text = re.sub(r'\\gamma', 'gamma', text)
    text = re.sub(r'\\delta', 'delta', text)
    text = re.sub(r'\\ell', 'l', text)
    text = re.sub(r'\\hbar', 'hbar', text)
    text = re.sub(r'\\cdot', '·', text)
    text = re.sub(r'\\times', 'x', text)
    text = re.sub(r'\\to', '->', text)
    text = re.sub(r'\\rightarrow', '->', text)
    text = re.sub(r'\\xrightarrow\{([^}]+)\}', r'--\1-->', text)
    text = re.sub(r'\\sqrt\{([^}]+)\}', r'sqrt(\1)', text)
    text = re.sub(r'\\frac\{([^}]+)\}\{([^}]+)\}', r'(\1)/(\2)', text)
    text = re.sub(r'\\mathbb\{R\}', 'R', text)
    text = re.sub(r'\\mathbb\{Z\}', 'Z', text)
    text = re.sub(r'\\mathcal\{([^}]+)\}', r'\1', text)
    text = re.sub(r'\$([^$]+)\$', r'\1', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

full_text = header

for sec_filename in sections_order:
    sec_path = os.path.join(paper_dir, "sections", sec_filename)
    if os.path.exists(sec_path):
        with open(sec_path, "r", encoding="utf-8") as f:
            raw_sec = f.read()
            full_text += "\n\n" + clean_latex(raw_sec)

with open(out_txt_path, "w", encoding="utf-8") as f:
    f.write(full_text)

print(f"Generated {out_txt_path} ({len(full_text)} characters, {len(full_text.splitlines())} lines)")
