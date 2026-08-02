import numpy as np
from scipy.optimize import minimize
from src.eft.scalar_potential import scalar_potential

def eps(tau):
    V_p = scalar_potential(tau + 1e-4)
    V_m = scalar_potential(tau - 1e-4)
    V_c = scalar_potential(tau)
    if V_c == 0: return 100
    dV = (V_p - V_m) / 2e-4
    return 0.5 * (dV / V_c)**2

def objective(tau):
    e = eps(tau[0])
    w0 = -1.0 + 2.0 * e / (1.0 + e)
    return (w0 - (-0.9745))**2

res = minimize(objective, [0.5], bounds=[(0.01, 2.0)])
print("Best tau:", res.x[0])
print("w0:", -1.0 + 2.0 * eps(res.x[0]) / (1.0 + eps(res.x[0])))
