"""Exp 3: the projection trap, quantified.

Setup: a 2D CA on a W x H torus. H = hidden ("extra") dimension size.
The 1D observer sees a projection. Two projection operators:

  PARITY  P(x) = XOR over the hidden column   (a collective/global mode)
  SLICE   P(x) = c(x, 0)                      (a "brane" observer)

Two meta-laws:
  LINEAR    c' = up ^ down ^ left ^ right
  NONLINEAR c' = up ^ down ^ left ^ right ^ (self & left)

Algebra predicts a 2x2 matrix of outcomes:
  linear + parity   : projection closes EXACTLY (P' = P(x-1)^P(x+1) = rule 90)
                      -> reducible. The lucky case: observable commutes with law.
  linear + slice    : even a LINEAR meta-law is irreducible on a brane
                      (slice depends on hidden neighbors).
  nonlinear + parity: collapses to coin-flip fast (AND term shreds parity).
  nonlinear + slice : intermediate, decays with H.

Measurement: predict projected row t+1 from row t using
  - all 256 elementary (radius-1) rules      -> best accuracy
  - best learned radius-r lookup rule (train/test split), r = 1..4
Sweep hidden dimension H in {1,2,4,8,16,32}.
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import json, os

rng = np.random.default_rng(7)
OUT = os.path.join(os.path.dirname(__file__), "figs")
os.makedirs(OUT, exist_ok=True)
results = {}

W = 509                       # prime: avoids rule-90 nilpotency on 2^k torus
T_TRAIN, T_TEST, BURN = 600, 300, 60

def step2d(grid, nonlinear):
    up, dn = np.roll(grid, -1, 0), np.roll(grid, 1, 0)
    lf, rt = np.roll(grid, 1, 1), np.roll(grid, -1, 1)
    out = up ^ dn ^ lf ^ rt
    if nonlinear:
        out ^= grid & lf
    return out

def run_projection(H, nonlinear, steps, proj):
    grid = rng.integers(0, 2, (H, W), dtype=np.uint8)
    rows = np.empty((steps, W), np.uint8)
    for _ in range(BURN):
        grid = step2d(grid, nonlinear)
    for t in range(steps):
        rows[t] = np.bitwise_xor.reduce(grid, axis=0) if proj == "parity" else grid[0]
        grid = step2d(grid, nonlinear)
    return rows

def neighborhood_codes(rows, r):
    T, Wd = rows.shape
    codes = np.zeros((T, Wd), np.int64)
    for off in range(-r, r + 1):
        codes = (codes << 1) | np.roll(rows, -off, axis=1)
    return codes

def fit_lookup(tr, te, r):
    ci, co = neighborhood_codes(tr[:-1], r), tr[1:]
    n = 1 << (2 * r + 1)
    ones = np.bincount(ci.ravel(), weights=co.ravel().astype(float), minlength=n)
    tot = np.bincount(ci.ravel(), minlength=n)
    table = (ones * 2 > tot).astype(np.uint8)
    pred = table[neighborhood_codes(te[:-1], r)]
    return float((pred == te[1:]).mean())

def fit_256(te):
    codes, target = neighborhood_codes(te[:-1], 1), te[1:]
    accs = np.zeros(256)
    for rule in range(256):
        tab = np.array([(rule >> i) & 1 for i in range(8)], np.uint8)
        accs[rule] = float((tab[codes] == target).mean())
    b = int(np.argmax(accs))
    return accs[b], b, accs

Hs = [1, 2, 4, 8, 16, 32]
radii = [1, 2, 3, 4]
data = {}
for law, nl in [("linear", False), ("nonlinear", True)]:
    for proj in ["parity", "slice"]:
        for H in Hs:
            rows = run_projection(H, nl, T_TRAIN + T_TEST, proj)
            tr, te = rows[:T_TRAIN], rows[T_TRAIN:]
            b256, brule, accs = fit_256(te)
            data[(law, proj, H)] = {
                "best256": b256, "best_rule": brule,
                "lookup": {r: fit_lookup(tr, te, r) for r in radii},
                "density": float(rows.mean())}
            if law == "nonlinear" and proj == "slice" and H == 8:
                np.save(f"{OUT}/acc256_nl_slice_H8.npy", accs)
                np.save(f"{OUT}/proj_nl_slice_H8.npy", rows[:160])
            if law == "nonlinear" and proj == "slice" and H == 1:
                np.save(f"{OUT}/proj_nl_slice_H1.npy", rows[:160])

results["exp3"] = {f"{l}|{p}|H={H}": v for (l, p, H), v in data.items()}

# ---------- coupling-strength sweep: the real control knob ----------
# Visible layer follows its exact 1D law, EXCEPT a static sparse set of sites
# (density p) where the hidden dimension leaks in: c'(x,0) ^= up_hidden & mask.
# Hidden layers run the full 2D nonlinear law. p = "dimensional leakage".
def run_coupled(H, p, steps):
    grid = rng.integers(0, 2, (H, W), dtype=np.uint8)
    mask = (rng.random(W) < p).astype(np.uint8)
    rows = np.empty((steps, W), np.uint8)
    for t in range(BURN + steps):
        nxt = step2d(grid, True)
        lf0 = np.roll(grid[0], 1)
        vis = lf0 ^ np.roll(grid[0], -1) ^ (grid[0] & lf0)   # exact 1D law
        nxt[0] = vis ^ (grid[1 % H] & mask)                  # leakage term
        if t >= BURN:
            rows[t - BURN] = grid[0]
        grid = nxt
    return rows

ps = [0.0, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0]
coupled = {}
for p in ps:
    rows = run_coupled(8, p, T_TRAIN + T_TEST)
    tr, te = rows[:T_TRAIN], rows[T_TRAIN:]
    b256, brule, accs = fit_256(te)
    coupled[p] = {"best256": b256, "best_rule": brule,
                  "lookup": {r: fit_lookup(tr, te, r) for r in radii}}
    if p == 0.2:
        np.save(f"{OUT}/acc256_coupled_p02.npy", accs)
results["exp3_coupling"] = {str(p): v for p, v in coupled.items()}

# ---------- figures ----------
p1 = np.load(f"{OUT}/proj_nl_slice_H1.npy"); p8 = np.load(f"{OUT}/proj_nl_slice_H8.npy")
fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2))
for ax, p, ttl in [(axes[0], p1, "H=1: an exact 1D law exists (found: 100% acc)"),
                   (axes[1], p8, "H=8: hidden dimension projected out")]:
    ax.imshow(p[:, :256], cmap="binary", aspect="auto", interpolation="nearest")
    ax.set(title=ttl, xlabel="x", ylabel="t")
fig.suptitle("Same kind of observable, different ontology - can you tell which hides a dimension?")
fig.tight_layout(); fig.savefig(f"{OUT}/fig3a_projections.png", dpi=140); plt.close(fig)

fig, (ax, ax2) = plt.subplots(1, 2, figsize=(11.5, 4.7))
styles = {("linear", "parity"): ("tab:blue", "o", "-"),
          ("linear", "slice"): ("tab:blue", "o", "--"),
          ("nonlinear", "parity"): ("tab:red", "s", "-"),
          ("nonlinear", "slice"): ("tab:red", "s", "--")}
for (law, proj), (col, mk, ls) in styles.items():
    ys = [data[(law, proj, H)]["lookup"][4] for H in Hs]
    ax.plot(Hs, ys, marker=mk, ls=ls, color=col, label=f"{law} law, {proj} observer")
ax.axhline(0.5, color="gray", ls=":", lw=1, label="coin flip")
ax.set(xscale="log", xlabel="hidden dimension size H",
       ylabel="best radius-4 1D rule, test accuracy",
       title="Reducibility depends on the meta-law algebra\nAND the projection operator")
ax.set_xticks(Hs); ax.set_xticklabels(Hs); ax.set_ylim(0.42, 1.04)
ax.legend(fontsize=8, loc="center left"); ax.grid(alpha=0.3)

for r, col in zip(radii, plt.cm.viridis(np.linspace(0.1, 0.8, len(radii)))):
    ax2.plot(ps, [coupled[p]["lookup"][r] for p in ps], "o-", color=col, label=f"radius {r}")
ax2.plot(ps, [coupled[p]["best256"] for p in ps], "k^--", label="best of 256 rules")
ax2.axhline(0.5, color="gray", ls=":", lw=1)
ax2.set(xlabel="dimensional leakage p (coupling density)", ylabel="test accuracy",
        title="The real knob is coupling, not size:\neffective-law accuracy vs leakage (H=8)")
ax2.legend(fontsize=8); ax2.grid(alpha=0.3)
fig.tight_layout(); fig.savefig(f"{OUT}/fig3b_acc_vs_H.png", dpi=140); plt.close(fig)

fig, ax = plt.subplots(figsize=(6.8, 4.6))
for p, col in zip(ps, plt.cm.plasma(np.linspace(0.05, 0.85, len(ps)))):
    ax.plot(radii, [coupled[p]["lookup"][r] for r in radii], "o-", color=col, label=f"p={p}")
ax.axhline(1.0, color="k", lw=0.7); ax.axhline(0.5, color="gray", ls=":", lw=1)
ax.set(xlabel="neighborhood radius r of fitted 1D rule", ylabel="test accuracy",
       title="Widening the 1D rule cannot buy back a missing dimension:\n"
             "accuracy saturates below 1 for any leakage p>0")
ax.set_xticks(radii); ax.legend(fontsize=8, title="leakage"); ax.grid(alpha=0.3)
fig.tight_layout(); fig.savefig(f"{OUT}/fig3c_acc_vs_radius.png", dpi=140); plt.close(fig)

accs = np.load(f"{OUT}/acc256_coupled_p02.npy")
order = np.argsort(accs)[::-1]
fig, ax = plt.subplots(figsize=(6.8, 4.2))
ax.bar(range(256), accs[order], width=1.0, color="tab:red", alpha=0.85)
best = order[0]
ax.annotate(f"best: rule {best} at {accs[best]:.3f}\na convincing WRONG law",
            xy=(0, accs[best]), xytext=(40, min(accs[best] + 0.04, 0.97)),
            arrowprops=dict(arrowstyle="->"), fontsize=9)
ax.axhline(0.5, color="gray", ls=":")
ax.set(xlabel="256 elementary rules (sorted by fit)", ylabel="accuracy on projected data",
       title="The local-optimum trap (leakage p=0.2, H=8):\n"
             "rule search converges confidently to a law that is not the law",
       ylim=(0.4, 1.0))
fig.tight_layout(); fig.savefig(f"{OUT}/fig3d_local_optimum.png", dpi=140); plt.close(fig)

print(json.dumps(results, indent=1))
