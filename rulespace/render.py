"""rulespace.render — the unified visualization standard.

Design contract (round-2 infrastructure):
  * CLOSED domain: everything lives on the torus; no open boundaries.
  * Three perceptual bands, always in the same order, same colormaps:
      GEOMETRY  band: local light speed c(x) = cos theta(x)   (blue)
      MATTER    band: energy/probability density rho(x)        (magma/red)
      VERDICT   band: the judges' scalar timelines with thresholds
                      (evaluation criteria live INSIDE the picture)
  * Frame data saved as .npz first (replayable), MP4 rendered via ffmpeg.
  * 1D runs -> curves + growing spacetime backdrop; 2D arrays -> imshow bands.
"""
import numpy as np, os, subprocess, tempfile, shutil
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

GEO_COLOR, MAT_COLOR = "#3a7bd5", "#d54e3a"

class Recorder:
    def __init__(self):
        self.t, self.c, self.rho, self.judges = [], [], [], {}

    def record(self, t, theta=None, rho=None, judges=None, c=None):
        self.t.append(t)
        self.c.append(np.cos(theta) if theta is not None else c)
        self.rho.append(np.array(rho))
        for k, v in (judges or {}).items():
            self.judges.setdefault(k, []).append(float(v))

    def save(self, path_npz):
        np.savez_compressed(path_npz, t=np.array(self.t), c=np.array(self.c),
                            rho=np.array(self.rho),
                            **{f"judge_{k}": np.array(v) for k, v in self.judges.items()})

    def to_mp4(self, path_mp4, title="", fps=18, thresholds=None, judge_good_above=None):
        thresholds = thresholds or {}
        judge_good_above = judge_good_above or {}
        c = np.array(self.c); rho = np.array(self.rho); ts = np.array(self.t)
        F, N = c.shape
        tmp = tempfile.mkdtemp()
        fig = plt.figure(figsize=(9.6, 7.2))
        gs = fig.add_gridspec(4, 1, height_ratios=[1.1, 1.1, 1.6, 0.9], hspace=0.45)
        axg, axm, axst, axj = [fig.add_subplot(gs[i]) for i in range(4)]
        fig.suptitle(title, fontsize=11)

        lg, = axg.plot([], [], color=GEO_COLOR, lw=1.6)
        axg.set_xlim(0, N); axg.set_ylim(np.nanmin(c) - 0.01, np.nanmax(c) + 0.01)
        axg.set_ylabel("GEOMETRY\nc(x)", fontsize=8); axg.grid(alpha=0.25)
        lm, = axm.plot([], [], color=MAT_COLOR, lw=1.4)
        axm.set_xlim(0, N); axm.set_ylim(0, np.nanmax(rho) * 1.08 + 1e-12)
        axm.set_ylabel("MATTER\nrho(x)", fontsize=8); axm.grid(alpha=0.25)
        st = axst.imshow(np.zeros((F, N)), aspect="auto", origin="lower", cmap="magma",
                         extent=[0, N, ts[0], ts[-1]], vmin=0, vmax=np.nanmax(rho))
        axst.set_ylabel("spacetime\n(matter)", fontsize=8)
        jlines = {}
        for k in self.judges:
            jlines[k], = axj.plot([], [], lw=1.4, label=k)
            if k in thresholds:
                axj.axhline(thresholds[k], ls=":", lw=1, color="gray")
        axj.set_xlim(ts[0], ts[-1]); axj.legend(fontsize=7, loc="upper right")
        axj.set_ylabel("VERDICT", fontsize=8); axj.grid(alpha=0.25)
        allj = [v for vs in self.judges.values() for v in vs]
        if allj:
            lo, hi = min(allj), max(allj)
            pad = 0.08 * (hi - lo + 1e-9)
            axj.set_ylim(lo - pad, hi + pad)
        stbuf = np.zeros((F, N))

        for f in range(F):
            lg.set_data(np.arange(N), c[f])
            lm.set_data(np.arange(N), rho[f])
            stbuf[f] = rho[f]
            st.set_data(stbuf)
            for k, ln in jlines.items():
                ln.set_data(ts[: f + 1], self.judges[k][: f + 1])
            verdicts = []
            for k in self.judges:
                v = self.judges[k][f]
                if k in thresholds:
                    good = v >= thresholds[k] if judge_good_above.get(k, True) else v <= thresholds[k]
                    verdicts.append(f"{k}={v:.3g} {'PASS' if good else 'FAIL'}")
                else:
                    verdicts.append(f"{k}={v:.3g}")
            axj.set_title("   ".join(verdicts), fontsize=8)
            fig.savefig(os.path.join(tmp, f"f{f:05d}.png"), dpi=100)
        plt.close(fig)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps),
                        "-i", os.path.join(tmp, "f%05d.png"),
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "24", path_mp4],
                       check=True)
        shutil.rmtree(tmp)
        return path_mp4
