#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Repo Facade — 给任意仓库生成一套「活的状态立面」门面资产。

设计原则（产品承诺）：
  1. 无面：没有人脸 / 拟人动物 / 表情包
  2. 身份连续：视觉 DNA 由仓库标识的哈希决定，同一仓库永远生成同一形象
  3. 零 JS：动画只用 SVG 内嵌 CSS @keyframes
  4. 可版本化：输出全是文本(SVG/HTML/MD)或确定性渲染的 PNG，可 git 回滚
  5. 母题来自结构，不是通用科技背景

用法：
  python3 facade.py --repo owner/name [--tagline "..."] [--badges "a|b|c"] [--out DIR]
  python3 facade.py --local /path/to/repo --name MyProject
"""
import argparse, hashlib, json, math, os, random, subprocess, sys, textwrap

# ---------- 字体 ----------
F_CJK = "/usr/share/fonts/truetype/alibaba-puhuiti/AlibabaPuHuiTi-2-75-SemiBold.ttf"
F_LAT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
F_LAT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def font(path, size):
    from PIL import ImageFont
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def has_cjk(s):
    return any('一' <= c <= '鿿' for c in (s or ""))


def pick_font(s, size):
    return font(F_CJK if has_cjk(s) else F_LAT, size)


# ---------- 视觉 DNA ----------
MOTIFS = ["percolation", "dendrite", "lattice"]
MOTIF_LABEL = {
    "percolation": "Percolation / 渗流阈值",
    "dendrite": "Dendritic growth / 枝晶生长",
    "lattice": "Lattice field / 晶格场",
}


class DNA:
    """由仓库标识确定性派生的视觉基因组。同一 repo → 同一 DNA → 同一形象。"""

    def __init__(self, key: str):
        h = hashlib.sha256(key.encode("utf-8")).hexdigest()
        self.hash = h
        rng = random.Random(int(h[:16], 16))
        self.motif = MOTIFS[int(h[2:4], 16) % len(MOTIFS)]
        self.hue = rng.uniform(150, 260)          # 冷色区间，避免俗艳
        self.seed = int(h[:8], 16)
        self.grid = rng.choice([9, 11, 13])
        self.rotate = rng.uniform(-14, 14)

    def ramp(self, n=6, s_min=0.30, s_max=0.66, l_min=0.42, l_max=0.72):
        """从主色相派生 n 阶色阶（HSL → hex）。"""
        out = []
        for i in range(n):
            t = i / max(1, n - 1)
            hh = (self.hue + 46 * t) % 360
            ss = s_min + (s_max - s_min) * (1 - t)
            ll = l_min + (l_max - l_min) * (1 - t * 0.55)
            out.append(hsl_hex(hh, ss, ll))
        return out

    def accent(self):
        return hsl_hex((self.hue + 180) % 360, 0.55, 0.68)

    def as_dict(self):
        return {"hash": self.hash[:12], "motif": self.motif, "hue": round(self.hue, 1),
                "grid": self.grid, "seed": self.seed, "ramp": self.ramp()}


def hsl_hex(h, s, l):
    import colorsys
    r, g, b = colorsys.hls_to_rgb(h / 360.0, l, s)
    return "#%02x%02x%02x" % (int(r * 255), int(g * 255), int(b * 255))


# ---------- 几何：三种母题 ----------
def geom_percolation(dna, n, p):
    """渗流网格：随机占位，返回 (格子列表, 是否贯通)。"""
    rng = random.Random(dna.seed + int(p * 1000))
    cells = []
    occupied = [[rng.random() < p for _ in range(n)] for _ in range(n)]
    # 标记贯通簇（从左边可达）
    seen = [[False] * n for _ in range(n)]
    stack = [(r, 0) for r in range(n) if occupied[r][0]]
    for r, c in stack:
        seen[r][c] = True
    while stack:
        r, c = stack.pop()
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            rr, cc = r + dr, c + dc
            if 0 <= rr < n and 0 <= cc < n and occupied[rr][cc] and not seen[rr][cc]:
                seen[rr][cc] = True
                stack.append((rr, cc))
    spanning = any(seen[r][n - 1] for r in range(n))
    for r in range(n):
        for c in range(n):
            if occupied[r][c]:
                cells.append({"r": r, "c": c, "span": seen[r][c],
                              "k": (r * 7 + c * 13) % 6})
    return cells, spanning


def geom_dendrite(dna, depth=5):
    """枝晶：递归分叉。返回线段列表。"""
    rng = random.Random(dna.seed)
    segs = []
    x0, y0 = 0.5, 0.98

    def grow(x, y, ang, length, d, branch):
        if d <= 0 or length < 0.012:
            return
        nx = x + math.cos(ang) * length
        ny = y - math.sin(ang) * length
        segs.append({"x1": x, "y1": y, "x2": nx, "y2": ny, "k": d, "w": branch})
        spread = rng.uniform(0.34, 0.62)
        for sgn in (-1, 1):
            grow(nx, ny, ang + sgn * spread * rng.uniform(0.7, 1.3),
                 length * rng.uniform(0.62, 0.80), d - 1, branch + 1)

    for i in range(3):
        grow(x0 + (i - 1) * 0.06, y0, math.pi / 2 + rng.uniform(-0.25, 0.25), 0.20, depth, 0)
    return segs


def geom_lattice(dna, n):
    """晶格场：节点 + 按距离连边。"""
    rng = random.Random(dna.seed)
    pts = []
    for i in range(n):
        for j in range(n):
            pts.append(((i + 0.5) / n + rng.uniform(-0.03, 0.03),
                        (j + 0.5) / n + rng.uniform(-0.03, 0.03)))
    edges = []
    for a in range(len(pts)):
        for b in range(a + 1, len(pts)):
            dx, dy = pts[a][0] - pts[b][0], pts[a][1] - pts[b][1]
            d = math.hypot(dx, dy)
            if d < 1.45 / n:
                edges.append({"x1": pts[a][0], "y1": pts[a][1],
                              "x2": pts[b][0], "y2": pts[b][1],
                              "k": int(d * n * 6) % 6, "w": 0})
    return pts, edges


# ---------- SVG 生成 ----------
def svg_motif(dna, x, y, w, h, animate=True, p=None, opacity=1.0):
    """把母题画进 (x,y,w,h) 的局部坐标里，返回 svg 片段 + defs。"""
    ramp = dna.ramp()
    parts = []
    if dna.motif == "percolation":
        n = dna.grid
        p = p if p is not None else 0.62
        cells, spanning = geom_percolation(dna, n, p)
        pad = 0.06
        cw = w * (1 - 2 * pad) / n
        ch = h * (1 - 2 * pad) / n
        for i, c in enumerate(cells):
            cx = x + w * pad + c["c"] * cw
            cy = y + h * pad + c["r"] * ch
            col = ramp[c["k"]] if c["span"] else ramp[5]
            op = (0.95 if c["span"] else 0.42) * opacity
            delay = (c["c"] * 0.055 + c["r"] * 0.012) if c["span"] else 0.0
            anim = ""
            if animate and c["span"]:
                anim = (f' style="animation:rf-in .9s ease-out {delay:.2f}s both"')
            parts.append(f'<rect x="{cx:.2f}" y="{cy:.2f}" width="{cw*0.82:.2f}" '
                         f'height="{ch*0.82:.2f}" rx="{cw*0.16:.2f}" fill="{col}" '
                         f'opacity="{op:.2f}"{anim}/>')
        return "".join(parts), spanning
    elif dna.motif == "dendrite":
        segs = geom_dendrite(dna)
        for i, s in enumerate(segs):
            x1 = x + s["x1"] * w; y1 = y + s["y1"] * h
            x2 = x + s["x2"] * w; y2 = y + s["y2"] * h
            col = ramp[min(5, s["k"])]
            lw = max(0.6, 3.4 - s["w"] * 0.55)
            anim = ""
            if animate:
                L = math.hypot(x2 - x1, y2 - y1)
                anim = (f' style="stroke-dasharray:{L:.1f};stroke-dashoffset:{L:.1f};'
                        f'animation:rf-grow .8s ease-out {s["w"]*0.16:.2f}s forwards"')
            parts.append(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
                         f'stroke="{col}" stroke-width="{lw:.2f}" stroke-linecap="round" '
                         f'opacity="{opacity:.2f}"{anim}/>')
        return "".join(parts), True
    else:
        pts, edges = geom_lattice(dna, dna.grid)
        for e in edges:
            x1 = x + e["x1"] * w; y1 = y + e["y1"] * h
            x2 = x + e["x2"] * w; y2 = y + e["y2"] * h
            anim = ""
            if animate:
                L = math.hypot(x2 - x1, y2 - y1)
                anim = (f' style="stroke-dasharray:{L:.1f};stroke-dashoffset:{L:.1f};'
                        f'animation:rf-grow .7s ease-out {(e["x1"]*1.4):.2f}s forwards"')
            parts.append(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
                         f'stroke="{ramp[e["k"]]}" stroke-width="1.1" '
                         f'opacity="{0.80*opacity:.2f}"{anim}/>')
        for i, (px, py) in enumerate(pts):
            parts.append(f'<circle cx="{x+px*w:.2f}" cy="{y+py*h:.2f}" r="{w*0.006:.2f}" '
                         f'fill="{ramp[i%6]}" opacity="{0.9*opacity:.2f}"/>')
        return "".join(parts), True


KEYFRAMES = """
  @keyframes rf-in   { from{opacity:0} to{opacity:.95} }
  @keyframes rf-grow { to{stroke-dashoffset:0} }
  @keyframes rf-breathe { 0%,100%{opacity:.55} 50%{opacity:.95} }
  @keyframes rf-pulse { 0%,100%{opacity:.5} 50%{opacity:1} }
  @keyframes rf-spin  { to{transform:rotate(360deg)} }
  @keyframes rf-jolt  { 0%{transform:translate(0,0)} 20%{transform:translate(4px,-2px)}
                        40%{transform:translate(-3px,2px)} 100%{transform:translate(0,0)} }
""".replace("  ", " ").strip()


def svg_wrap(w, h, body, extra_css=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
            f'width="{w}" height="{h}" role="img">\n'
            f'<style>{KEYFRAMES}\n{extra_css}</style>\n{body}\n</svg>\n')


def build_hero(dna, name, tagline, w=1200, h=420):
    ramp = dna.ramp()
    bg = "#0e1116"
    body = [f'<rect width="{w}" height="{h}" fill="{bg}"/>']
    # 母题放在右侧 52%
    mx, my, mw, mh = w * 0.50, h * 0.14, w * 0.44, h * 0.72
    frag, _ = svg_motif(dna, mx, my, mw, mh, animate=True)
    body.append(f'<g transform="rotate({dna.rotate:.1f} {mx+mw/2:.0f} {my+mh/2:.0f})">{frag}</g>')
    # 左侧文字（距边缘 56）
    lx = 56
    body.append(f'<text x="{lx}" y="{h*0.30:.0f}" font-family="{F_LAT_B}" font-size="40" '
                f'fill="#e8ecf2" font-weight="bold">{esc(name[:28])}</text>')
    # tagline 折行
    tl = textwrap.wrap(tagline or "", width=26)[:2]
    for i, line in enumerate(tl):
        fs = 'font-family="%s"' % (F_CJK if has_cjk(line) else F_LAT)
        body.append(f'<text x="{lx}" y="{h*0.30+52+i*34:.0f}" {fs} font-size="21" '
                    f'fill="#98a3b3">{esc(line)}</text>')
    # motif 标签 + 色阶条
    fs = 'font-family="%s"' % (F_CJK if has_cjk(MOTIF_LABEL[dna.motif]) else F_LAT)
    body.append(f'<text x="{lx}" y="{h-56:.0f}" {fs} font-size="14" fill="#5c6675">'
                f'{esc(MOTIF_LABEL[dna.motif])} · DNA {dna.hash[:8]}</text>')
    for i, c in enumerate(ramp):
        body.append(f'<rect x="{lx+i*26}" y="{h-38}" width="20" height="6" rx="3" fill="{c}"/>')
    return svg_wrap(w, h, "".join(body))


# 六状态：颜色 + 节奏 + 语义
STATES = [
    ("idle",     "静置",   "4s 慢呼吸 · 冷色低亮度",       "rf-breathe 4s ease-in-out infinite", 0.55),
    ("thinking", "推演",   "0.8s 快脉冲 · 琥珀偏移",       "rf-pulse .8s ease-in-out infinite",   0.75),
    ("busy",     "执行",   "持续旋转 · 亮度拉高",           "rf-spin 6s linear infinite",          1.00),
    ("blocked",  "受阻",   "脉冲冻结 · 低饱和红",           "none",                                0.40),
    ("error",    "失败",   "红色 · 一次抽动后静止",         "rf-jolt .5s ease-out 1 forwards",     0.90),
    ("success",  "达成",   "短暂暖脉冲 → 回落 idle",        "rf-pulse 1.1s ease-out 2 forwards",   0.85),
]
STATE_COLORS = {
    "idle":    ("#3f7d5a", "#7fd6a6"),
    "thinking":("#9c6416", "#f0c060"),
    "busy":    ("#2f6fa8", "#8fd0ff"),
    "blocked": ("#6b3a3a", "#a46565"),
    "error":   ("#8f2f2f", "#e5655f"),
    "success": ("#a8752a", "#f5c97a"),
}


def build_states(dna, cell_w=480, cell_h=160, cols=3, rows=2):
    W = cell_w * cols
    H = cell_h * rows
    body = [f'<rect width="{W}" height="{H}" fill="#0e1116"/>']
    for idx, (key, cn, hint, anim, op) in enumerate(STATES):
        cx = (idx % cols) * cell_w
        cy = (idx // cols) * cell_h
        dark, light = STATE_COLORS[key]
        body.append(f'<rect x="{cx+6}" y="{cy+6}" width="{cell_w-12}" height="{cell_h-12}" '
                    f'rx="10" fill="#141922" stroke="{dark}" stroke-opacity=".55"/>')
        # 缩略母题
        frag, _ = svg_motif(dna, cx + cell_w - 132, cy + 26, 110, 88,
                            animate=(key in ("idle", "thinking", "busy")), opacity=0.9)
        g = f'<g style="animation:{anim}" transform-origin="{cx+cell_w-77}px {cy+70}px">{frag}</g>' \
            if anim != "none" else f'<g opacity="{op}">{frag}</g>'
        body.append(g)
        fs = 'font-family="%s"' % F_CJK
        body.append(f'<text x="{cx+22}" y="{cy+52}" {fs} font-size="24" fill="{light}">{cn}</text>')
        body.append(f'<text x="{cx+22}" y="{cy+76}" font-family="{F_LAT}" font-size="13" '
                    f'fill="#6b7686">{key}</text>')
        body.append(f'<text x="{cx+22}" y="{cy+104}" {fs} font-size="12" fill="#8b95a5">'
                    f'{esc(hint)}</text>')
        # 节奏条
        dur = {"idle": 4.0, "thinking": 0.8, "busy": 6.0, "blocked": 0, "error": 0.5, "success": 1.1}[key]
        body.append(f'<rect x="{cx+22}" y="{cy+124}" width="{90*(dur/4 if dur else 0.14):.0f}" '
                    f'height="4" rx="2" fill="{light}" opacity=".8"/>')
    return svg_wrap(W, H, "".join(body))


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


# ---------- PNG：社交预览 ----------
def build_preview_png(dna, name, tagline, badges, out, W=1280, H=640):
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (W, H), "#0e1116")
    d = ImageDraw.Draw(img)
    ramp = dna.ramp()
    # 右侧母题（用 SVG 中转渲染，保证与 hero 同一 DNA）
    import cairosvg
    frag, _ = svg_motif(dna, 0, 0, 560, 520, animate=False)
    mot = svg_wrap(560, 520, f'<rect width="560" height="520" fill="#0e1116"/>{frag}')
    tmp = os.path.join(os.path.dirname(out), "_motif_tmp.png")
    cairosvg.svg2png(bytestring=mot.encode(), write_to=tmp, output_width=560, output_height=520)
    m = Image.open(tmp).convert("RGB")
    img.paste(m, (W - 620, 60))
    os.remove(tmp)
    # 文字
    x = 72
    d.text((x, 118), name[:24], font=pick_font(name, 62), fill="#e8ecf2")
    tl = textwrap.wrap(tagline or "", width=22)[:2]
    for i, line in enumerate(tl):
        d.text((x, 208 + i * 42), line, font=pick_font(line, 27), fill="#98a3b3")
    # 3 badges
    bx = x
    for i, b in enumerate((badges or [])[:3]):
        tw = d.textlength(b, font=pick_font(b, 22))
        bw = tw + 34
        d.rounded_rectangle([bx, 340, bx + bw, 388], radius=10,
                            outline=ramp[i * 2 % 6], width=2)
        d.text((bx + 17, 352), b, font=pick_font(b, 22), fill=ramp[i * 2 % 6])
        bx += bw + 16
    # 底部 DNA
    d.text((x, H - 74), f'{MOTIF_LABEL[dna.motif]}  ·  DNA {dna.hash[:8]}',
           font=pick_font(MOTIF_LABEL[dna.motif], 17), fill="#5c6675")
    for i, c in enumerate(ramp):
        d.rounded_rectangle([x + i * 30, H - 48, x + i * 30 + 24, H - 40], radius=4, fill=c)
    img.save(out)
    return out


# ---------- 一页式演示台 ----------
def build_index(dna, name, tagline, badges, repo_url=None):
    ramp = dna.ramp()
    acc = dna.accent()
    badges_html = "".join(
        f'<span class="badge" style="border-color:{ramp[i*2%6]};color:{ramp[i*2%6]}">{esc(b)}</span>'
        for i, b in enumerate((badges or [])[:3]))
    repo_line = f'<p class="repo"><a href="{esc(repo_url)}">{esc(repo_url)}</a></p>' if repo_url else ""
    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(name)}</title>
<style>
:root{{--bg:#0e1116;--fg:#e8ecf2;--mut:#98a3b3;--dim:#5c6675;--acc:{acc}}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--fg);
 font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;
 line-height:1.65}}
.wrap{{max-width:880px;margin:0 auto;padding:48px 24px 80px}}
h1{{font-size:clamp(28px,5.2vw,44px);margin:0 0 12px;letter-spacing:-.02em}}
.sub{{color:var(--mut);font-size:clamp(15px,2.6vw,19px);margin:0 0 28px}}
.badges{{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:20px}}
.badge{{border:1px solid;padding:5px 13px;border-radius:999px;font-size:14px}}
.repo a{{color:var(--acc);text-decoration:none;font-size:14px;word-break:break-all}}
section{{margin:44px 0;padding-top:28px;border-top:1px solid #1e2531}}
h2{{font-size:20px;margin:0 0 8px}}
p{{color:var(--mut);font-size:15px;margin:6px 0}}
img,svg{{max-width:100%;height:auto;display:block;border-radius:10px;background:#141922}}
table{{width:100%;border-collapse:collapse;font-size:14px;margin-top:10px}}
td,th{{padding:7px 8px;border-bottom:1px solid #1e2531;text-align:left;color:var(--mut)}}
th{{color:var(--fg);font-weight:600}}
code{{background:#141922;padding:2px 6px;border-radius:4px;font-size:13px;color:{acc}}}
footer{{margin-top:56px;color:var(--dim);font-size:13px}}
</style></head><body><div class="wrap">
<h1>{esc(name)}</h1>
<p class="sub">{esc(tagline)}</p>
<div class="badges">{badges_html}</div>
{repo_line}
<section>
<h2>形象 / Identity</h2>
<p>母题 <b>{esc(MOTIF_LABEL[dna.motif])}</b> · 视觉 DNA <code>{dna.hash[:12]}</code></p>
<p>形象由仓库标识的哈希确定性派生——同一个仓库永远生成同一张脸，不每次重画。</p>
<img src="social-preview.png" alt="social preview">
<object type="image/svg+xml" data="identity.svg" style="width:100%;min-height:200px"></object>
</section>
<section>
<h2>状态 / States</h2>
<p>六个状态，颜色与呼吸节奏各不相同；动画为 SVG 内嵌 CSS，无 JavaScript。</p>
<object type="image/svg+xml" data="states.svg" style="width:100%;min-height:300px"></object>
<table><tr><th>状态</th><th>节奏</th><th>含义</th></tr>
{"".join(f'<tr><td>{cn} · {k}</td><td>{esc(h.split(" · ")[0])}</td><td>{esc(h.split(" · ")[-1])}</td></tr>' for k,cn,h,_,_ in STATES)}
</table>
</section>
<section>
<h2>怎么用</h2>
<p><code>python3 facade.py --repo owner/name --out ./assets</code></p>
<p>产出：social-preview.png(1280×640) · identity.svg(1200×420) · states.svg · README_SNIPPET.md · 本页</p>
</section>
<footer>无 JavaScript · 无外部依赖 · 可版本化回滚 · 没有人脸</footer>
</div></body></html>
"""


def build_snippet(dna, name, tagline, badges, repo_url=None):
    ramp = dna.ramp()
    badges_txt = " · ".join(f"`{b}`" for b in (badges or [])[:3])
    return f"""# {name}

{tagline}

{badges_txt}

> 视觉母题：{MOTIF_LABEL[dna.motif]} · DNA `{dna.hash[:12]}`
> 形象由仓库标识哈希确定性派生，同一仓库永远同一张脸。

<p align="center">
  <img src="assets/identity.svg" width="600" alt="identity">
</p>

## 状态

| 状态 | 节奏 | 含义 |
|---|---|---|
""" + "\n".join(f"| {cn} · `{k}` | {h.split(' · ')[0]} | {h.split(' · ')[-1]} |"
                 for k, cn, h, _, _ in STATES) + f"""

## 技术约束

- 不跑 JavaScript，动画只用 SVG 内嵌 CSS `@keyframes`
- 不依赖外部库与运行时接口
- SVG 可版本化、可回滚
- 无面：没有人脸 / 拟人动物 / 表情包

{f"仓库：{repo_url}" if repo_url else ""}
"""


# ---------- 主流程 ----------
def from_github(owner_name, token=None):
    """抓仓库元信息；没有 token 也能跑（限 60 次/小时）。"""
    url = f"https://api.github.com/repos/{owner_name}"
    cmd = ["curl", "-s", "-m", "20", "-H", "Accept: application/vnd.github+json"]
    if token:
        cmd += ["-H", f"Authorization: token {token}"]
    cmd.append(url)
    try:
        r = json.loads(subprocess.run(cmd, capture_output=True, text=True).stdout or "{}")
    except Exception:
        r = {}
    if "full_name" not in r:
        return None
    return {
        "name": r.get("name"),
        "desc": r.get("description") or "",
        "topics": r.get("topics", []),
        "lang": r.get("language") or "",
        "stars": r.get("stargazers_count", 0),
        "url": r.get("html_url"),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", help="owner/name")
    ap.add_argument("--local", help="本地路径（离线模式）")
    ap.add_argument("--name", default=None)
    ap.add_argument("--tagline", default=None)
    ap.add_argument("--badges", default="", help="用 | 分隔，最多 3 个")
    ap.add_argument("--out", default="./facade_out")
    ap.add_argument("--token", default=None)
    a = ap.parse_args()

    meta = None
    if a.repo:
        tk = a.token or (open(".gh_token").read().strip() if os.path.exists(".gh_token") else None)
        meta = from_github(a.repo, tk)
        if not meta:
            print(f"[warn] 抓不到 {a.repo}（无网络/无 token），退回离线模式", file=sys.stderr)
    key = a.repo or a.local or a.name or "unnamed"
    name = a.name or (meta["name"] if meta else os.path.basename((a.local or key).rstrip("/")))
    def clip_tagline(s, n=74):
        s = (s or "").strip().replace("\n", " ")
        # 优先在第一个句读处切断
        for sep in ("。", ". ", " / ", "；"):
            i = s.find(sep)
            if 12 < i <= n:
                return s[:i]
        return s if len(s) <= n else s[:n].rstrip() + "…"

    tagline = a.tagline or (clip_tagline(meta["desc"]) if meta and meta["desc"] else
                            f"{name} — 一套可复现的实验与自检材料")
    badges = [b.strip() for b in a.badges.split("|") if b.strip()]
    if not badges and meta:
        badges = [f"★ {meta['stars']}", meta["lang"], (meta["topics"] or [""])[0]][:3]
        badges = [b for b in badges if b]

    dna = DNA(key)
    os.makedirs(a.out, exist_ok=True)
    files = {}
    files["identity.svg"] = build_hero(dna, name, tagline)
    files["states.svg"] = build_states(dna)
    files["index.html"] = build_index(dna, name, tagline, badges, meta["url"] if meta else None)
    files["README_SNIPPET.md"] = build_snippet(dna, name, tagline, badges,
                                                meta["url"] if meta else None)
    for fn, content in files.items():
        with open(os.path.join(a.out, fn), "w", encoding="utf-8") as f:
            f.write(content)
    png = os.path.join(a.out, "social-preview.png")
    build_preview_png(dna, name, tagline, badges, png)
    with open(os.path.join(a.out, "dna.json"), "w", encoding="utf-8") as f:
        json.dump(dna.as_dict(), f, ensure_ascii=False, indent=2)
    print(json.dumps({"repo": key, "name": name, "motif": dna.motif,
                      "dna": dna.hash[:12], "out": os.path.abspath(a.out)},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
