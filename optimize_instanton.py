import numpy as np
from scipy.optimize import minimize
from src.eft.scalar_potential import scalar_potential

def eps(tau, A, a):
    V_p = scalar_potential(tau + 1e-4, instanton_A=A, instanton_a=a)
    V_m = scalar_potential(tau - 1e-4, instanton_A=A, instanton_a=a)
    V_c = scalar_potential(tau, instanton_A=A, instanton_a=a)
    if V_c == 0: return 100
    dV = (V_p - V_m) / 2e-4
    return 0.5 * (dV / V_c)**2

def objective(params):
    A, a = params
    e = eps(0.50, A, a)
    w0 = -1.0 + 2.0 * e / (1.0 + e)
    return (w0 - (-0.9745))**2

res = minimize(objective, [0.1, 6.28], bounds=[(1e-5, 10.0), (0.1, 20.0)])
print("Best A:", res.x[0], "Best a:", res.x[1])
print("w0:", -1.0 + 2.0 * eps(0.50, res.x[0], res.x[1]) / (1.0 + eps(0.50, res.x[0], res.x[1])))
