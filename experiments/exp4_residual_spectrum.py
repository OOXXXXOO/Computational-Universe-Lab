"""Exp 4: irreducible residual spectrum + inversion of hidden structure.

Mori-Zwanzig prediction: projecting out a dimension converts it into
(memory kernel + noise) in the visible dynamics. Therefore:
  - widening SPATIAL radius r of the fitted 1D model: no gain (proved in exp3)
  - deepening TEMPORAL history d: gain, IF the hidden sector is correlated
  - if the hidden sector is delta-correlated (xor rule), nothing helps:
    that part of the residual is truly irreducible noise.
The SHAPE of the irreducible residual spectrum measures the hidden sector's
correlation structure -- observable entirely from inside the projection.

Inversion pipeline (the "way out"):
  1. per-site error map  -> image the leakage sites (recover mask)
  2. at leak sites, residual = hidden field read out directly
     (observer knows the exact clean law from non-leak sites)
  3. from the read-out field: hidden density, temporal correlation
     -> compare against ground truth never shown to the observer.

Stages: gen | fit | ml | figs   (cached in exp4_cache.npz / exp4_results.json)
"""
import numpy as np, json, os, sys

DIR = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(DIR, "figs")
CACHE = os.path.join(DIR, "exp4_cache.npz")
RES = os.path.join(DIR, "exp4_results.json")
rng = np.random.default_rng(11)

W, H, P = 509, 8, 0.2
T_TOT, BURN = 3000, 80
T_TRAIN = 2200

def step2d(g, kind):
    up, dn = np.roll(g, -1, 0), np.roll(g, 1, 0)
    lf, rt = np.roll(g, 1, 1), np.roll(g, -1, 1)
    if kind == "xor":
        return up ^ dn ^ lf ^ rt ^ (g & lf)
    s = up + dn + lf + rt
    return ((s == 2) | ((s == 1) & (g == 1))).astype(np.uint8)   # "tot"

def law1d(v):
    lf, rt = np.roll(v, 1), np.roll(v, -1)
    return lf ^ rt ^ (v & lf)

def gen(kind, seed):
    r = np.random.default_rng(seed)
    grid = r.integers(0, 2, (H, W), dtype=np.uint8)
    mask = (r.random(W) < P).astype(np.uint8)
    rows = np.empty((T_TOT, W), np.uint8)
    hid1 = np.empty((T_TOT, W), np.uint8)          # ground truth, never shown to observer
    for t in range(BURN + T_TOT):
        nxt = step2d(grid, kind)
        nxt[0] = law1d(grid[0]) ^ (grid[1] & mask)
        if t >= BURN:
            rows[t - BURN] = grid[0]
            hid1[t - BURN] = grid[1]
        grid = nxt
    return rows, hid1, mask

def contexts(rows, rr, dd):
    """packed integer context: rows[t-dd+1..t] x offsets -rr..rr ; predicts rows[t+1]"""
    T = rows.shape[0]
    n = T - dd
    codes = np.zeros((n, W), np.int64)
    for a in range(dd):
        for off in range(-rr, rr + 1):
            codes = (codes << 1) | np.roll(rows[dd - 1 - a: dd - 1 - a + n], -off, axis=1)
    return codes, rows[dd:]

def lookup_fit(rows, rr, dd):
    codes, target = contexts(rows, rr, dd)
    ntr = T_TRAIN - dd
    ci, co = codes[:ntr], target[:ntr]
    ce, te = codes[ntr:], target[ntr:]
    nbits = (2 * rr + 1) * dd
    ncode = 1 << nbits
    ones = np.bincount(ci.ravel(), weights=co.ravel().astype(float), minlength=ncode)
    tot = np.bincount(ci.ravel(), minlength=ncode)
    tab = (ones * 2 > tot).astype(np.uint8)
    acc = float((tab[ce] == te).mean())
    # conditional entropy H(y|ctx), Laplace-smoothed on train, evaluated on test
    p1 = (ones + 0.5) / (tot + 1.0)
    pt = p1[ce]
    eps = 1e-12
    ent = float(-(te * np.log2(pt + eps) + (1 - te) * np.log2(1 - pt + eps)).mean())
    return acc, ent

CONFIGS = [(1,1),(2,1),(3,1),(4,1),(1,2),(1,3),(1,4),(1,5),(2,2),(2,3)]

if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else "all"
    results = json.load(open(RES)) if os.path.exists(RES) else {}

    if stage in ("gen", "all"):
        store = {}
        for kind, seed in [("xor", 21), ("tot", 22)]:
            rows, hid1, mask = gen(kind, seed)
            store[f"rows_{kind}"] = rows; store[f"hid1_{kind}"] = hid1; store[f"mask_{kind}"] = mask
        np.savez_compressed(CACHE, **store)
        print("gen done")

    if stage in ("fit", "all"):
        Z = np.load(CACHE)
        for kind in ["xor", "tot"]:
            rows = Z[f"rows_{kind}"]
            spec = {}
            for (rr, dd) in CONFIGS:
                acc, ent = lookup_fit(rows, rr, dd)
                spec[f"r{rr}d{dd}"] = {"acc": acc, "ent": ent}
            results[f"spectrum_{kind}"] = spec
            # ---- inversion pipeline ----
            hid1, mask = Z[f"hid1_{kind}"], Z[f"mask_{kind}"]
            pred = law1d(rows[T_TRAIN:-1].T).T if False else None
            vis = rows
            lawpred = np.array([law1d(vis[t]) for t in range(T_TRAIN, T_TOT - 1)])
            errmap = (lawpred != vis[T_TRAIN + 1:]).astype(float).mean(axis=0)   # per-site
            # image the mask: threshold at half of max plateau
            thr = errmap.max() * 0.25
            mask_hat = (errmap > thr).astype(np.uint8)
            mask_acc = float((mask_hat == mask).mean())
            # read hidden field at recovered leak sites: residual = hid1 exactly
            leak_idx = np.where(mask_hat == 1)[0]
            resid = np.array([law1d(vis[t]) ^ vis[t + 1] for t in range(T_TRAIN, T_TOT - 1)])
            readout = resid[:, leak_idx].astype(float)          # observer's map of hid1
            truth = hid1[T_TRAIN:T_TOT - 1, leak_idx].astype(float)
            read_match = float((readout == truth).mean())
            dens_hat = float(readout.mean())
            dens_true = float(hid1.mean())
            ac_hat = float(np.corrcoef(readout[:-1].ravel(), readout[1:].ravel())[0, 1])
            ac_true = float(np.corrcoef(hid1[:-1].ravel(), hid1[1:].ravel())[0, 1])
            p_hat = float(mask_hat.mean())
            results[f"invert_{kind}"] = {
                "mask_recovery_acc": mask_acc, "p_hat": p_hat, "p_true": P,
                "hid_readout_match": read_match,
                "hid_density_hat": dens_hat, "hid_density_true": dens_true,
                "hid_lag1corr_hat": ac_hat, "hid_lag1corr_true": ac_true}
            np.save(os.path.join(OUT, f"errmap_{kind}.npy"), errmap)
            np.save(os.path.join(OUT, f"readout_{kind}.npy"), readout[:200])
            np.save(os.path.join(OUT, f"truth_{kind}.npy"), truth[:200])
        json.dump(results, open(RES, "w"), indent=1)
        print("fit done")

    if stage in ("ml", "all"):
        from sklearn.linear_model import LogisticRegression
        from sklearn.neural_network import MLPClassifier
        Z = np.load(CACHE)
        MLCFG = [(1, 1), (4, 1), (1, 3), (2, 3)]
        for kind in ["xor", "tot"]:
            rows = Z[f"rows_{kind}"]
            ml = {}
            for (rr, dd) in MLCFG:
                codes, target = contexts(rows, rr, dd)
                nbits = (2 * rr + 1) * dd
                ntr = T_TRAIN - dd
                def unpack(c):
                    return ((c[:, None] >> np.arange(nbits)[::-1]) & 1).astype(np.float32)
                ri = np.random.default_rng(3).choice(ntr * W, size=120000, replace=False)
                Xtr = unpack(codes[:ntr].ravel()[ri]); ytr = target[:ntr].ravel()[ri]
                rj = np.random.default_rng(4).choice((T_TOT - dd - ntr) * W, size=60000, replace=False)
                Xte = unpack(codes[ntr:].ravel()[rj]); yte = target[ntr:].ravel()[rj]
                lo = LogisticRegression(max_iter=300).fit(Xtr, ytr)
                acc_lo = float(lo.score(Xte, yte))
                mp = MLPClassifier((64,), max_iter=25, random_state=0,
                                   early_stopping=False).fit(Xtr, ytr)
                acc_mp = float(mp.score(Xte, yte))
                ml[f"r{rr}d{dd}"] = {"logistic": acc_lo, "mlp64": acc_mp}
            results[f"ml_{kind}"] = ml
        json.dump(results, open(RES, "w"), indent=1)
        print("ml done")

    if stage in ("figs", "all"):
        import matplotlib; matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        results = json.load(open(RES))
        Z = np.load(CACHE)

        # fig4a: accuracy spectrum - radius vs depth, both hidden sectors
        fig, axes = plt.subplots(1, 2, figsize=(11.6, 4.6), sharey=True)
        for ax, kind, ttl in [(axes[0], "xor", "delta-correlated hidden sector (xor)"),
                              (axes[1], "tot", "correlated hidden sector (tot)")]:
            sp = results[f"spectrum_{kind}"]
            rs = [1, 2, 3, 4]; ds = [1, 2, 3, 4, 5]
            ax.plot(rs, [sp[f"r{r}d1"]["acc"] for r in rs], "o-", color="tab:red",
                    label="widen space: radius r (d=1)")
            ax.plot(ds, [sp[f"r1d{d}"]["acc"] for d in ds], "s-", color="tab:blue",
                    label="deepen time: history d (r=1)")
            ml = results[f"ml_{kind}"]
            ax.plot([1], [ml["r1d1"]["mlp64"]], "k*", ms=11, label="MLP-64 (r1d1)")
            ax.plot([3], [ml["r1d3"]["mlp64"]], "k*", ms=11)
            ax.set(xlabel="r  or  d", title=ttl); ax.grid(alpha=0.3)
            ax.legend(fontsize=8)
        axes[0].set_ylabel("test accuracy")
        fig.suptitle("Mori-Zwanzig in a toy universe: a projected-out dimension becomes MEMORY, not neighborhood", fontsize=11)
        fig.tight_layout()
        fig.savefig(f"{OUT}/fig4a_memory_vs_radius.png", dpi=140); plt.close(fig)

        # fig4b: conditional-entropy (irreducible residual) spectrum
        fig, ax = plt.subplots(figsize=(7.0, 4.4))
        for kind, col in [("xor", "tab:red"), ("tot", "tab:blue")]:
            sp = results[f"spectrum_{kind}"]
            ds = [1, 2, 3, 4, 5]
            ax.plot(ds, [sp[f"r1d{d}"]["ent"] for d in ds], "o-", color=col,
                    label=f"{kind}: H(y|past d rows)")
        ax.set(xlabel="history depth d (r=1)", ylabel="conditional entropy (bits/cell)",
               title="Irreducible residual spectrum: what memory can and cannot buy back\n"
                     "flat curve = true noise; falling curve = hidden dynamics")
        ax.grid(alpha=0.3); ax.legend()
        fig.tight_layout(); fig.savefig(f"{OUT}/fig4b_entropy_spectrum.png", dpi=140); plt.close(fig)

        # fig4c: imaging the leak sites
        fig, axes = plt.subplots(2, 1, figsize=(10.5, 4.6), sharex=True)
        for ax, kind in [(axes[0], "xor"), (axes[1], "tot")]:
            errmap = np.load(f"{OUT}/errmap_{kind}.npy")
            mask = Z[f"mask_{kind}"]
            inv = results[f"invert_{kind}"]
            ax.plot(errmap, lw=0.9, color="tab:orange", label="per-site error rate (observable)")
            my = np.where(mask == 1)[0]
            ax.plot(my, np.full_like(my, -0.02, dtype=float), "|", color="tab:blue",
                    ms=8, label="true leak sites (hidden truth)")
            ax.set(ylabel=f"{kind}", xlim=(0, W))
            ax.legend(fontsize=8, loc="upper right")
            ax.set_title(f"mask recovery {100*inv['mask_recovery_acc']:.1f}%   "
                         f"p_hat={inv['p_hat']:.3f} (true {P})", fontsize=9)
        axes[1].set_xlabel("site x")
        fig.suptitle("Imaging the extra dimension's coupling sites from residuals alone")
        fig.tight_layout(); fig.savefig(f"{OUT}/fig4c_mask_imaging.png", dpi=140); plt.close(fig)

        # fig4d: the observer's reconstructed map of the hidden field
        fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.2))
        ro = np.load(f"{OUT}/readout_tot.npy"); tr = np.load(f"{OUT}/truth_tot.npy")
        inv = results["invert_tot"]
        axes[0].imshow(ro.T, cmap="binary", aspect="auto", interpolation="nearest")
        axes[0].set(title="observer's readout of hidden field (leak sites x time)",
                    xlabel="t", ylabel="leak site #")
        axes[1].imshow(tr.T, cmap="binary", aspect="auto", interpolation="nearest")
        axes[1].set(title="ground truth hidden field (never shown)", xlabel="t")
        fig.suptitle(f"Reading the hidden dimension through its leaks: match={100*inv['hid_readout_match']:.1f}%, "
                     f"density {inv['hid_density_hat']:.3f} vs {inv['hid_density_true']:.3f}, "
                     f"lag-1 corr {inv['hid_lag1corr_hat']:.2f} vs {inv['hid_lag1corr_true']:.2f}")
        fig.tight_layout(); fig.savefig(f"{OUT}/fig4d_hidden_readout.png", dpi=140); plt.close(fig)
        print("figs done")
