import numpy as np, json, os
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

DIR = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(DIR, "figs")
r = json.load(open(os.path.join(DIR, "exp5_results.json")))
times = np.load(f"{OUT}/exp5_times.npy")
gs = [0.05, 0.1, 0.2, 0.4, 0.8, 1.6]
nhs = [2, 4, 6, 8]

# fig5a: trace distance dynamics
fig, axes = plt.subplots(1, 2, figsize=(11.6, 4.4), sharey=True)
for g, col in [(0.1, "tab:green"), (0.4, "tab:blue"), (1.6, "tab:red")]:
    D = np.load(f"{OUT}/exp5_D_nh2_g{g}.npy")
    axes[0].plot(times, D, color=col, lw=1.3, label=f"g={g}")
    D = np.load(f"{OUT}/exp5_D_nh8_g{g}.npy")
    axes[1].plot(times, D, color=col, lw=1.3, label=f"g={g}")
axes[0].set(title="small hidden dimension (n_h=2): loud echoes",
            xlabel="time", ylabel="trace distance D(t) seen by 2-qubit observer")
axes[1].set(title="large hidden sector (n_h=8): masquerades as Markovian decay",
            xlabel="time")
for ax in axes: ax.legend(); ax.grid(alpha=0.3)
fig.suptitle("Partial trace as projection: every rise of D(t) is information flowing BACK from the hidden dimension")
fig.tight_layout(); fig.savefig(f"{OUT}/fig5a_trace_distance.png", dpi=140); plt.close(fig)

# fig5b: BLP measure vs g and vs n_h
fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.4))
for nh, col in zip(nhs, plt.cm.viridis(np.linspace(0.1, 0.85, len(nhs)))):
    axes[0].plot(gs, [r[f"nh{nh}_g{g}"]["blp"] for g in gs], "o-", color=col, label=f"n_h={nh}")
axes[0].set(xscale="log", xlabel="coupling g (dimensional leakage)",
            ylabel="BLP non-Markovianity N", title="leakage meter: N grows with coupling")
axes[0].legend(); axes[0].grid(alpha=0.3, which="both")
for g, col in [(0.4, "tab:blue"), (0.8, "tab:orange"), (1.6, "tab:red")]:
    axes[1].plot(nhs, [r[f"nh{nh}_g{g}"]["blp"] for nh in nhs], "s-", color=col, label=f"g={g}")
axes[1].set(xlabel="hidden sector size n_h", ylabel="N",
            title="a LARGE hidden sector hides itself:\nechoes fade as n_h grows (KK-echo analog)")
axes[1].legend(); axes[1].grid(alpha=0.3)
fig.tight_layout(); fig.savefig(f"{OUT}/fig5b_blp.png", dpi=140); plt.close(fig)

# fig5c: inversion g_hat ~ g from short-time purity leakage
fig, ax = plt.subplots(figsize=(6.4, 4.6))
for nh, col in zip(nhs, plt.cm.viridis(np.linspace(0.1, 0.85, len(nhs)))):
    sc = [np.sqrt(r[f"nh{nh}_g{g}"]["leak_c"]) for g in gs]
    ax.loglog(gs, sc, "o-", color=col, label=f"n_h={nh}")
ax.loglog(gs, [0.57 * g for g in gs], "k--", lw=1, label="slope 1 (perturbative)")
ax.set(xlabel="true coupling g", ylabel="sqrt(short-time purity leakage rate)",
       title="Inversion from inside the projection: g_hat proportional to g\n"
             "(deviation at g=1.6 = measured breakdown of perturbation theory)")
ax.legend(fontsize=8); ax.grid(alpha=0.3, which="both")
fig.tight_layout(); fig.savefig(f"{OUT}/fig5c_inversion.png", dpi=140); plt.close(fig)
print("figs done")
