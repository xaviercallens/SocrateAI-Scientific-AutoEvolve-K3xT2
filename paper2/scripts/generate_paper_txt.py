#!/usr/bin/env python3
"""Generate plain text version of Paper 2."""
import os, re

script_dir = os.path.dirname(os.path.abspath(__file__))
paper_dir = os.path.dirname(script_dir)

sections_order = [
    "01_introduction.tex", "02_hypergraph_model.tex", "03_continuum_limit.tex",
    "04_scalar_mass.tex", "05_gw_predictions.tex", "06_anisotropy_hd.tex",
    "07_hadamard_mask.tex", "08_results.tex", "09_conclusion.tex", "10_acknowledgments.tex"
]

header = """================================================================================
GRAVITATIONAL WAVES FROM TOPOLOGICAL DEFECTS IN K4 HYPERGRAPH PREGEOMETRY:
SPECTRAL PREDICTIONS FOR NANOGRAV AND SKA
================================================================================

Author: Xavier Callens (Independent Researcher)
Date: July 31, 2026

================================================================================
"""

def clean_latex(text):
    text = re.sub(r'\\section\*?\{([^}]+)\}', r'\n================================================================================\n\1\n================================================================================\n', text)
    text = re.sub(r'\\subsection\{([^}]+)\}', r'\n--------------------------------------------------------------------------------\n\1\n--------------------------------------------------------------------------------\n', text)
    text = re.sub(r'\\paragraph\{([^}]+)\}', r'\n* \1: ', text)
    text = re.sub(r'\\cite\{([^}]+)\}', r'[\1]', text)
    text = re.sub(r'\\label\{([^}]+)\}', '', text)
    text = re.sub(r'\\ref\{([^}]+)\}', r'\1', text)
    text = re.sub(r'\\eqref\{([^}]+)\}', r'(\1)', text)
    text = re.sub(r'\\emph\{([^}]+)\}', r'_\1_', text)
    text = re.sub(r'\\textbf\{([^}]+)\}', r'**\1**', text)
    text = re.sub(r'\\texttt\{([^}]+)\}', r'`\1`', text)
    text = re.sub(r'\\mathrm\{([^}]+)\}', r'\1', text)
    text = re.sub(r'\\begin\{equation\}(.*?)\\end\{equation\}', r'\n[Equation: \1]\n', text, flags=re.DOTALL)
    text = re.sub(r'\\begin\{table\}.*?\\end\{table\}', r'\n[Table]\n', text, flags=re.DOTALL)
    text = re.sub(r'\\begin\{enumerate\}', '', text)
    text = re.sub(r'\\end\{enumerate\}', '', text)
    text = re.sub(r'\\begin\{itemize\}', '', text)
    text = re.sub(r'\\end\{itemize\}', '', text)
    text = re.sub(r'\\item\s+', '  * ', text)
    text = re.sub(r'\\fbox\{\\parbox[^}]*\{([^}]*)\}\}', r'\1', text)
    text = re.sub(r'\\noindent', '', text)
    text = re.sub(r'\\medskip', '', text)
    text = re.sub(r'\\boxed\{([^}]+)\}', r'[\1]', text)
    text = re.sub(r'\$([^$]+)\$', r'\1', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

full_text = header
for sec in sections_order:
    path = os.path.join(paper_dir, "sections", sec)
    if os.path.exists(path):
        with open(path) as f:
            full_text += "\n\n" + clean_latex(f.read())

out = os.path.join(paper_dir, "main.txt")
with open(out, "w") as f:
    f.write(full_text)
print(f"Generated {out} ({len(full_text)} chars, {len(full_text.splitlines())} lines)")
