"""Exp 5: quantum projection = partial trace; non-Markovianity = leakage meter.

System: chain of qubits. Qubits 0,1 = visible universe. Qubits 2..n_h+1 = hidden
dimension. Heisenberg couplings: J=1 inside visible and inside hidden;
g = visible-hidden bond ("dimensional leakage"). Small random z-fields on the
hidden sector make it non-degenerate ("chaotic bath").

The 2-qubit observer sees rho_v(t) = Tr_hidden |psi(t)><psi(t)|.

Measurements:
 1. BLP non-Markovianity: evolve two initially distinguishable visible states
    (same hidden state), trace distance D(t) = 0.5*||rho1-rho2||_1.
    Markovian dynamics => D monotone decreasing. Revivals = information
    flowing BACK from the hidden dimension = detectable echo.
    N_BLP = sum of positive increments of D.
 2. Inversion: short-time purity leakage 1 - Tr(rho^2) ~ c*g^2*t^2.
    Estimate g_hat = sqrt(c)/const from visible data alone; check g_hat ~ g.

Predictions:
  small n_h (small compact hidden dimension): strong revivals (KK-echo analog)
  large n_h: bath swallows information, dynamics looks Markovian
             -> a LARGE hidden sector hides itself; a SMALL one echoes.
"""
import numpy as np, json, os, sys

DIR = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(DIR, "figs")
RES = os.path.join(DIR, "exp5_results.json")

sx = np.array([[0, 1], [1, 0]], complex)
sy = np.array([[0, -1j], [1j, 0]])
sz = np.array([[1, 0], [0, -1]], complex)
I2 = np.eye(2, dtype=complex)

def op(n, i, s):
    m = np.array([[1]], complex)
    for q in range(n):
        m = np.kron(m, s if q == i else I2)
    return m

def heisenberg(n, bonds, hz):
    d = 2 ** n
    Hm = np.zeros((d, d), complex)
    for (i, j, J) in bonds:
        for s in (sx, sy, sz):
            Hm += 0.25 * J * op(n, i, s) @ op(n, j, s)
    for i, h in hz:
        Hm += 0.5 * h * op(n, i, sz)
    return Hm

def run(n_h, g, times, rng):
    n = 2 + n_h
    bonds = [(0, 1, 1.0), (1, 2, g)] + [(i, i + 1, 1.0) for i in range(2, n - 1)]
    hz = [(i, rng.uniform(-0.5, 0.5)) for i in range(2, n)]
    Hm = heisenberg(n, bonds, hz)
    E, V = np.linalg.eigh(Hm)
    dh = 2 ** n_h
    env = rng.normal(size=dh) + 1j * rng.normal(size=dh)
    env /= np.linalg.norm(env)
    # visible pair: Bell-like antipodal states (maximal initial distance)
    v1 = np.zeros(4, complex); v1[0] = 1 / np.sqrt(2); v1[3] = 1 / np.sqrt(2)
    v2 = np.zeros(4, complex); v2[0] = 1 / np.sqrt(2); v2[3] = -1 / np.sqrt(2)
    out = {}
    for tag, v in [("1", v1), ("2", v2)]:
        psi0 = np.kron(v, env)
        phi = V.conj().T @ psi0
        # psi(t) for all times: V @ (exp(-iEt)*phi)
        ph = np.exp(-1j * np.outer(E, times)) * phi[:, None]
        Psi = V @ ph                                     # dim x ntimes
        out[tag] = Psi
    D = np.empty(len(times)); Pur = np.empty(len(times))
    for a in range(len(times)):
        r1 = out["1"][:, a].reshape(4, dh); r2 = out["2"][:, a].reshape(4, dh)
        rho1 = r1 @ r1.conj().T; rho2 = r2 @ r2.conj().T
        D[a] = 0.5 * np.abs(np.linalg.eigvalsh(rho1 - rho2)).sum()
        Pur[a] = float(np.real(np.trace(rho1 @ rho1)))
    return D, Pur

def blp(D):
    dD = np.diff(D)
    return float(dD[dD > 0].sum())

if __name__ == "__main__":
    nh_list = [int(x) for x in sys.argv[1].split(",")] if len(sys.argv) > 1 else [2, 4, 6]
    gs = [0.05, 0.1, 0.2, 0.4, 0.8, 1.6]
    times = np.linspace(0, 40, 500)
    results = json.load(open(RES)) if os.path.exists(RES) else {}
    curves = {}
    for n_h in nh_list:
        rng = np.random.default_rng(100 + n_h)   # fixed bath per n_h
        for g in gs:
            D, Pur = run(n_h, g, times, rng)
            key = f"nh{n_h}_g{g}"
            results[key] = {"blp": blp(D), "Dfinal": float(D[-1]), "Dmin": float(D.min())}
            # short-time leakage rate for inversion: 1-P ~ c t^2
            w = times < 1.5
            c = np.polyfit(times[w] ** 2, 1 - Pur[w], 1)[0]
            results[key]["leak_c"] = float(max(c, 1e-12))
            np.save(f"{OUT}/exp5_D_nh{n_h}_g{g}.npy", D)
    np.save(f"{OUT}/exp5_times.npy", times)
    json.dump(results, open(RES, "w"), indent=1)
    print("done", nh_list)
