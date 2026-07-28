"""Generate the repo cover banner (1280x640 + @2x).

Schematic of the v2 program state: an (emergence-degree ε, constraint-scale σ)
map with the three closed-loop benchmark points and the v1-sealed spin-2 wall.
This is a clearly-labeled schematic (示意图), not a measured plot — positions
are qualitative. Re-run after any program-state pivot to keep the cover honest.
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
# macOS CJK fallback (DejaVu Sans has no CJK glyphs); text() uses family="sans-serif"
plt.rcParams["font.sans-serif"] = ["Hiragino Sans GB", "Arial Unicode MS", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
from matplotlib.patches import FancyBboxPatch, Rectangle
from matplotlib.lines import Line2D
import os

# Palette tokens (from visualizations/dashboards/program_atlas.html)
BG = "#f4f6f5"
CARD = "#ffffff"
INK = "#1e2c35"
MUTED = "#647079"
HAIR = "#aebac4"
TEAL = "#0f9a8d"      # emergence / live
WARM = "#c1741f"      # coupled / mixed
BLUE = "#3d6db0"      # maxwell / spin-1
RED = "#c34459"       # sealed / unreachable
GREEN = "#2f9b5c"

FIG_W, FIG_H = 12.8, 6.4  # inches @ 100dpi -> 1280x640


def make(dpi=100, out="repo_cover.png"):
    fig = plt.figure(figsize=(FIG_W, FIG_H), dpi=dpi)
    fig.patch.set_facecolor(BG)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1280)
    ax.set_ylim(0, 640)
    ax.axis("off")

    # Card
    card = FancyBboxPatch((40, 40), 1200, 560, boxstyle="round,pad=0,rounding_size=18",
                          linewidth=0, facecolor=CARD, zorder=0)
    ax.add_patch(card)

    # --- Title block (left) ---
    ax.text(72, 560, "投影规则空间纲领", fontsize=30, fontweight="bold",
            color=INK, family="sans-serif")
    ax.text(72, 524, "Projective Rule-Space Program", fontsize=14,
            color=MUTED, family="sans-serif")
    ax.text(72, 488, "涌现边界制图 · Emergence Boundary Cartography (v2)",
            fontsize=13, color=TEAL, family="sans-serif", fontweight="bold")

    # tagline
    ax.text(72, 92,
            "在局域 QCA 规则空间里,用数学自洽与 Maxwell / Einstein / Yang–Mills 实验做 QA 剪枝,",
            fontsize=11, color=MUTED, family="sans-serif")
    ax.text(72, 72,
            "寻找投影后涌现场论的规则等价类——涌现不是二值的,是可测量的连续边界。",
            fontsize=11, color=MUTED, family="sans-serif")
    ax.text(72, 50, "v2 · 2026-07 · 诚实边界:墙这边测清可达的形状,墙那边测清不可达。",
            fontsize=10, color=HAIR, family="sans-serif", style="italic")

    # --- Map panel (right) ---
    px0, py0, pw, ph = 640, 150, 560, 380
    ax.add_patch(Rectangle((px0, py0), pw, ph, facecolor="#fbfcfc",
                           edgecolor=HAIR, linewidth=1, zorder=1))

    # axes labels
    ax.text(px0 + pw / 2, py0 - 26, "涌现度  ε   (0 手搭  →  1 涌现)",
            fontsize=11, color=INK, ha="center", family="sans-serif")
    ax.text(px0 - 16, py0 + ph / 2, "约束标度  σ   (松  →  严)",
            fontsize=11, color=INK, ha="center", va="center",
            rotation=90, family="sans-serif")

    # schematic accessibility frontier (faint gradient band)
    import numpy as np
    xs = np.linspace(0, 1, 100)
    # a soft frontier curve: stricter constraint reachable at lower emergence
    ys = 0.85 - 0.55 * xs
    ax.plot(px0 + xs * pw, py0 + ys * ph, color=TEAL, linewidth=1.6,
            alpha=0.35, zorder=2)

    # v1 sealed region (high-ε + strict-σ corner) — hatched
    sealed = Rectangle((px0 + 0.62 * pw, py0 + 0.62 * ph),
                       0.38 * pw, 0.38 * ph, facecolor=RED, alpha=0.10,
                       edgecolor=RED, linewidth=1.2, hatch="///", zorder=3)
    ax.add_patch(sealed)
    ax.text(px0 + 0.81 * pw, py0 + 0.81 * ph,
            "v1 封存\n自旋2 M3\n结构性不可达\n(四承诺全要)",
            fontsize=8.5, color=RED, ha="center", va="center",
            family="sans-serif", fontweight="bold", zorder=5)

    def pt(fx, fy, color, label, sub, dx=14, dy=14):
        ax.scatter([px0 + fx * pw], [py0 + fy * ph], s=120, color=color,
                   edgecolor="white", linewidth=1.5, zorder=6)
        ax.annotate(label, (px0 + fx * pw, py0 + fy * ph),
                    xytext=(px0 + fx * pw + dx, py0 + fy * ph + dy),
                    fontsize=10.5, color=INK, fontweight="bold",
                    family="sans-serif", zorder=7)
        ax.annotate(sub, (px0 + fx * pw, py0 + fy * ph),
                    xytext=(px0 + fx * pw + dx, py0 + fy * ph + dy - 14),
                    fontsize=8.5, color=MUTED, family="sans-serif", zorder=7)

    # three closed-loop benchmark points (qualitative placement)
    pt(0.06, 0.82, INK, "R30", "ε=0 · 手搭复形存在性", dx=14, dy=-2)
    pt(0.50, 0.55, WARM, "M2′ 耦合点", "(ε_geo=0, ε_mat=1)", dx=12, dy=-26)
    pt(0.92, 0.30, BLUE, "M1′ Maxwell", "ε=1 · 涌现自旋1", dx=-150, dy=-2)

    # legend chips
    chips = [
        (INK, "R30 存在性定理"),
        (BLUE, "M1′ Maxwell 闭环"),
        (WARM, "M2′ 耦合闭环"),
        (RED, "v1 封存墙"),
    ]
    cx = px0 + 6
    cy = py0 + ph - 20
    for color, txt in chips:
        ax.scatter([cx], [cy], s=70, color=color, edgecolor="white",
                   linewidth=1.2, zorder=6)
        ax.text(cx + 9, cy, txt, fontsize=8.5, color=INK, va="center",
                family="sans-serif", zorder=7)
        cx += 10 + 6.5 * len(txt) + 12

    # "示意图" marker
    ax.text(px0 + pw - 8, py0 + 10, "示意图 · schematic", fontsize=8,
            color=HAIR, ha="right", va="bottom", family="sans-serif",
            style="italic", zorder=8)

    out_dir = os.path.join(os.path.dirname(__file__), "assets")
    fig.savefig(os.path.join(out_dir, out), dpi=dpi, facecolor=BG)
    plt.close(fig)


if __name__ == "__main__":
    make(dpi=100, out="repo_cover.png")
    make(dpi=200, out="repo_cover@2x.png")
    print("cover written: assets/repo_cover.png (+@2x)")
