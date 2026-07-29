# v2 设计规范：Computational Universe Lab 视觉系统与图像生成提示词

*状态：视觉方向经用户批准，2026-07-29。视觉蓝本：
`visualizations/dashboards/program_atlas.html`。本规范只规定品牌表达，不改变任何科学判定。*

## 一、品牌层级

- 一级品牌：**Computational Universe Lab**
- 研究计划副标题：**Projective Rule-Space Program**
- 当前纲领说明：**Emergence Boundary Cartography · v2**
- 标志母题：**规则空间中的涌现边界**。不得用普通宇宙、行星、火箭、原子轨道等泛科学图标
  取代这一母题。

## 二、视觉语言

整体气质是“可复核的科学图册”：编辑式、克制、精密、可信，像研究仪器输出与高质量科学
期刊专题页的结合，而不是科幻娱乐界面。

### 2.1 色彩

| 角色 | 深色主题 | 用途 |
|---|---|---|
| ground | `#0B1013` | 主背景 |
| panel | `#111B22` | 图表与卡片 |
| line | `#1E2C35` | 发丝线、网格、分隔 |
| ink | `#DDE6EC` | 主标题、关键轮廓 |
| ink-dim | `#AEBAC4` | 正文、次级信息 |
| muted | `#7F909D` | 坐标、注释、元数据 |
| metric | `#45D4C6` | 几何、光、边界、测量 |
| matter | `#E7A24E` | 物质、能量、关键数字 |
| pass | `#5FD08A` | 已确立、PASS |
| sealed | `#E5687A` | 封存边界、结构性不可达 |

青绿与琥珀只用于具有语义的信号，不能作为无意义装饰。大面积色彩保持低饱和，关键节点才
提高亮度。

### 2.2 字体与排版

- 展示标题：Iowan Old Style / Palatino / Georgia 一类编辑式 old-style serif；
- 数字、坐标、状态和标签：SF Mono / JetBrains Mono / Fira Code；
- 大标题使用纸白色、紧凑字距；技术标签使用全大写、宽字距；
- 标题负责提出科学命题，等宽字负责给出证据与状态；
- 避免未来主义无衬线字、霓虹描边字、金属 3D 字和游戏界面风格。

### 2.3 图形母题

主图形由四种元素构成：

1. 稀疏离散格点或规则空间网格；
2. 一条平滑、可测的边界曲线，区分 lawful / non-lawful 区域；
3. 三个已测锚点，分别提示 `ε=0`、`ε=1` 与分扇区耦合点；
4. 极少量等高线、传播波前或测地线，表达“制图”和“极限测量”。

图形必须保持二维、平面、可缩放。禁止星球、银河漩涡、火箭、宇航员、DNA、芯片大脑、
六边形科技蜂巢和常见原子轨道。

## 三、Logo 图像生成提示词

建议先生成无文字图形标志，再以真实字体排版品牌名；若模型文字能力足够，可保留提示词中的
横向字标要求。

### 3.1 主提示词

```text
Design a rigorous flat vector identity for “Computational Universe Lab”, with the scientific concept
of emergence-boundary cartography as the core symbol. Create one compact geometric emblem: a sparse
discrete rule-space lattice crossed by one smooth measurable boundary curve, with three precisely
placed anchor nodes suggesting epsilon = 0, epsilon = 1, and a split coupled point. Let the negative
space very subtly suggest the initials C U L without turning the mark into an obvious monogram.

Visual language: editorial scientific atlas, research-instrument precision, quiet authority, minimal
geometry, mathematically balanced, memorable at favicon size. Use a near-black ground #0B1013,
paper-white #DDE6EC lines, emergence/geometry teal #45D4C6, and one restrained matter-energy amber
#E7A24E anchor. Hairline grid, crisp Bézier boundary, no glow except an almost imperceptible edge
luminosity, no gradients inside the logo mark.

Create a horizontal lockup with the exact words “COMPUTATIONAL UNIVERSE LAB” in a refined old-style
editorial serif similar to Iowan Old Style or Palatino, with a small monospaced secondary line reading
“PROJECTIVE RULE-SPACE PROGRAM”. Keep the symbol and typography optically balanced, generous negative
space, flat vector construction, clean SVG-like edges, brand-system quality, centered on a plain
near-black background. No additional words.

Output: one primary logo lockup only, 3:1 horizontal canvas, ultra-clean vector appearance, suitable
for repository headers, papers, dashboards, favicon reduction, and monochrome conversion.
```

### 3.2 负面提示词

```text
No planet, galaxy, nebula, rocket, astronaut, telescope, atom icon, orbital rings, DNA, brain,
microchip, circuit-board pattern, hexagon tech motif, infinity symbol, generic AI sparkle, cyberpunk,
purple neon, lens flare, glossy 3D, chrome, bevel, drop shadow, mascot, cartoon, stock-logo look,
busy star field, illegible typography, invented words, duplicated letters, excessive detail.
```

### 3.3 图标单独生成补句

当生成器不擅长文字时，将主提示词中横向字标段替换为：

```text
Generate the emblem only, with no letters and no text. Center it on a transparent background with
ample clear space. The mark must remain identifiable at 32×32 pixels and work in one-color form.
Output a single square 1:1 symbol, not a logo presentation sheet.
```

## 四、Repo cover 图像生成提示词

目标尺寸沿仓库现有资产契约：`1280×640`，并提供 `2560×1280` 二倍图。

### 4.1 主提示词

```text
Create a wide 2:1 editorial repository cover for “Computational Universe Lab”, inspired by a premium
scientific field atlas and a precision research dashboard. The subject is emergence-boundary
cartography in local quantum cellular-automaton rule space — not outer space.

Use a near-black #0B1013 background with subtle #111B22 instrument panels and hairline #1E2C35 grid
lines. Across the right two-thirds, visualize a sparse rule-space map: discrete lattice points,
fine contour lines, one elegant teal #45D4C6 boundary separating lawful and non-lawful regions, and
three measured anchor points. One anchor is paper white at epsilon = 0, one is bright teal at
epsilon = 1, and one is a restrained amber #E7A24E split-sector coupled point. Add a faint red
#E5687A sealed region beyond the boundary, rendered as sparse cartographic hatching rather than a
dramatic warning. Include a few thin white propagation curves bending through the measured field,
echoing geodesics and the visual grammar of experimental plots. Every line should look data-derived,
not decorative.

Reserve the left 38 percent as calm negative space for the title. Set the exact title
“COMPUTATIONAL UNIVERSE LAB” in large paper-white old-style editorial serif type, with the exact
monospaced subtitle “PROJECTIVE RULE-SPACE PROGRAM · EMERGENCE BOUNDARY CARTOGRAPHY · v2” below it.
Add one very small teal index label “ε × σ” and no other text. Typography must be crisp, correctly
spelled, restrained, and subordinate to the scientific map.

Mood: lucid, empirical, archival, quietly ambitious, mathematically literate, honest about measured
boundaries. Composition: asymmetric editorial layout, generous negative space, strong baseline grid,
flat 2D vector and data-visualization aesthetics, no photographic objects, no decorative clutter.
The image should feel like the cover of a serious computational-physics monograph and match a dark
scientific dashboard using serif headlines and monospaced measurements.

Output exactly 1280×640 pixels, edge-to-edge, no outer frame, suitable as the first image in a GitHub
README. Keep all critical title content inside a 7 percent safe margin.
```

### 4.2 负面提示词

```text
No literal universe photo, planet, Earth, galaxy, nebula, black hole illustration, rocket,
astronaut, telescope, atom icon, molecular ball-and-stick model, AI brain, circuit-board background,
hexagonal HUD, cyberpunk interface, purple-blue neon, excessive glow, lens flare, metallic 3D,
glassmorphism, glossy gradients, game UI, startup landing-page cliché, fake equations, random text,
misspelled words, watermark, logo mockup, device frame, photographic texture, clutter.
```

### 4.3 无文字稳健版

若生成器不能可靠生成准确文字，删除主提示词的排版段，替换为：

```text
Leave the left 38 percent intentionally empty and visually quiet for later typography. Do not render
any letters, numbers, symbols, labels, equations, or watermark. Keep the scientific map on the right
and maintain the 7 percent safe margin. The title will be typeset separately in a real font.
```

无文字底图生成后，标题必须由仓库脚本或排版软件叠加，避免错误文字进入正式资产。

## 五、验收标准

- 缩到 32×32 时 Logo 仍能看出“格点 + 边界 + 锚点”；
- Logo 单色化后不丢失轮廓；
- cover 在 README 宽度下先读到品牌名，再读到边界地图；
- 颜色均有科学语义，不出现无意义霓虹装饰；
- 不出现任何泛宇宙或泛 AI 图标；
- 生成器文字若有一处错误，整张图不得进入正式资产，必须采用无文字版后期排版；
- 视觉 PASS 不是科学 PASS，状态色不得越权表达实验裁定。
