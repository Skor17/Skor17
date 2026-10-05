"""Static profile cards (header, boot log, whoami, comms, stack, footer)."""

from __future__ import annotations

import math
import random

from svgkit import (BG, CRT, CYAN, DIM, DISPLAY, GREEN, HOT, LINE, MAGENTA, MID, MONO,
                    PANEL, SVG, crt_defs, frame, overlay)

W = 840          # desktop card width; phones get NARROW-wide cards with stacked columns
NARROW = 440
RAIN_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ@#$%&*+=<>:;|/\\?!"


def refresh_beam(svg: SVG) -> None:
    """A faint bright band that sweeps down the screen like a CRT refresh."""
    svg.defs.append(
        '<linearGradient id="beam" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{GREEN}" stop-opacity="0"/>'
        f'<stop offset=".5" stop-color="{GREEN}" stop-opacity=".07"/>'
        f'<stop offset="1" stop-color="{GREEN}" stop-opacity="0"/></linearGradient>'
    )
    svg.styles.append(
        f"@keyframes beam{{from{{transform:translateY(-80px)}}to{{transform:translateY({svg.h + 80}px)}}}}"
        ".beam{animation:beam 7s linear infinite}"
    )
    svg.add(f'<g class="beam"><rect x="1" y="0" width="{svg.w - 2}" height="80" fill="url(#beam)"/></g>')


def fit(font, s: str, size: float, max_w: float, spacing: float = 0) -> float:
    """Largest font size <= size at which s fits in max_w."""
    return min(size, size * max_w / font.width(s, size, spacing))


def digital_rain(svg: SVG, seed: int, height: int, cols: int, size: float = 17,
                 opacity: float = 1.0, clip: str = "") -> None:
    rnd = random.Random(seed)
    line = size * 1.05
    step = svg.w / cols
    max_h = 22 * line * 1.1
    svg.styles.append(
        f"@keyframes fall{{from{{transform:translateY({-max_h:.0f}px)}}to{{transform:translateY({height + 10}px)}}}}"
        ".rain{animation:fall linear infinite}"
        "@keyframes flick{0%,100%{opacity:1}50%{opacity:.25}}"
        ".fl{animation:flick 1.3s steps(2) infinite}"
    )
    out = [f'<g opacity="{opacity}" {clip}>']
    for c in range(cols):
        n = rnd.randint(8, 22)
        s = "".join(rnd.choice(RAIN_CHARS) for _ in range(n))
        # tail fades out, the leading glyph (bottom) glows near-white
        ops = [0.12 + 0.88 * (i / (n - 1)) ** 1.6 for i in range(n)]
        fills = [GREEN] * (n - 1) + [HOT]
        dur = rnd.uniform(5.5, 12)
        delay = -rnd.uniform(0, dur)
        x = step * (c + 0.5) + rnd.uniform(-2, 2)
        sz = size * rnd.choice((0.8, 0.9, 1, 1, 1, 1.1))
        out.append(
            f'<g class="rain" style="animation-duration:{dur:.2f}s;animation-delay:{delay:.2f}s">'
            + svg.column(s, x, 0, sz, line * sz / size, CRT, fills, ops)
            + "</g>"
        )
    out.append("</g>")
    svg.add("".join(out))


# ── HEADER ───────────────────────────────────────────────────────────────────
def header(p: dict, W: int = W) -> SVG:
    me = p["identity"]
    H = 300
    svg = SVG(W, H, f'{me["handle"]} // {me["name"]}',
              f'Matrix-style digital rain over a retro neon grid. {me["name"]}. '
              "[ SYSTEM INITIALIZED ] :: ACCESS GRANTED")
    crt_defs(svg)
    hz = 204  # horizon
    cx = W / 2
    svg.defs.append(
        f'<clipPath id="card"><rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="9"/></clipPath>'
        f'<clipPath id="sky"><rect x="0" y="0" width="{W}" height="{hz}"/></clipPath>'
        f'<clipPath id="floor"><rect x="0" y="{hz}" width="{W}" height="{H - hz}"/></clipPath>'
        '<linearGradient id="sun" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{HOT}"/><stop offset=".45" stop-color="{GREEN}"/>'
        f'<stop offset="1" stop-color="{DIM}"/></linearGradient>'
        f'<linearGradient id="floorfade" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{BG}" stop-opacity="1"/>'
        f'<stop offset=".35" stop-color="{BG}" stop-opacity=".55"/>'
        f'<stop offset="1" stop-color="{BG}" stop-opacity=".25"/></linearGradient>'
        '<radialGradient id="haze" cx="50%" cy="100%" r="60%">'
        f'<stop offset="0" stop-color="{GREEN}" stop-opacity=".35"/>'
        f'<stop offset="1" stop-color="{GREEN}" stop-opacity="0"/></radialGradient>'
        # sun stripes: thicker gaps towards the horizon (classic 80s sun)
        '<mask id="sunmask"><rect width="100%" height="100%" fill="#fff"/>'
        + "".join(f'<rect x="0" y="{hz - 6 - i * 9 - i * i * 0.6:.1f}" width="{W}" height="{4.2 - i * 0.55:.1f}" fill="#000"/>'
                  for i in range(7))
        + "</mask>"
    )
    svg.add(f'<g clip-path="url(#card)">', f'<rect width="{W}" height="{H}" fill="{BG}"/>')

    # digital rain behind everything
    digital_rain(svg, seed=17, height=H, cols=round(W / 16), opacity=0.5)

    # horizon haze + striped sun
    svg.add(
        f'<rect x="0" y="{hz - 140}" width="{W}" height="140" fill="url(#haze)"/>',
        f'<g clip-path="url(#sky)" mask="url(#sunmask)" opacity=".55">'
        f'<circle cx="{cx}" cy="{hz}" r="88" fill="url(#sun)"/></g>',
    )

    # neon floor: dark plate, radiating lines, horizontal lines that rush toward the viewer
    floor = [f'<g clip-path="url(#floor)">', f'<rect x="0" y="{hz}" width="{W}" height="{H - hz}" fill="{BG}" opacity=".88"/>']
    for i in range(-14, 15):
        xb = cx + i * 74
        floor.append(f'<line x1="{cx + i * 4:.1f}" y1="{hz}" x2="{xb:.1f}" y2="{H}" stroke="{GREEN}" stroke-width="1.2" opacity=".55"/>')
    svg.styles.append(
        f"@keyframes run{{from{{transform:translateY(0);opacity:0}}20%{{opacity:.8}}to{{transform:translateY({H - hz}px);opacity:1}}}}"
        ".hl{animation:run 3.2s cubic-bezier(.55,0,1,.6) infinite}"
    )
    for i in range(8):
        floor.append(f'<g class="hl" style="animation-delay:{-i * 0.4:.1f}s">'
                     f'<line x1="0" y1="{hz}" x2="{W}" y2="{hz}" stroke="{GREEN}" stroke-width="1.4"/></g>')
    floor.append(f'<rect x="0" y="{hz}" width="{W}" height="{H - hz}" fill="url(#floorfade)"/>')
    floor.append(f'<line x1="0" y1="{hz}" x2="{W}" y2="{hz}" stroke="{HOT}" stroke-width="1.5" filter="url(#glow)"/>')
    floor.append("</g>")
    svg.add(*floor)

    # glitching title
    title = me["handle"]
    ty = 120
    ts = fit(DISPLAY, title, 74, W - 56, 10)
    svg.styles.append(
        "@keyframes gA{0%,86%,100%{transform:translate(0,0);opacity:0}87%{transform:translate(-6px,1px);opacity:.9}"
        "89%{transform:translate(4px,-1px);opacity:.9}91%{transform:translate(-2px,0);opacity:.8}92%{opacity:0}}"
        "@keyframes gB{0%,86%,100%{transform:translate(0,0);opacity:0}87%{transform:translate(6px,-1px);opacity:.9}"
        "89%{transform:translate(-4px,1px);opacity:.9}91%{transform:translate(3px,0);opacity:.8}92%{opacity:0}}"
        "@keyframes slice{0%,88%,100%{transform:translateX(0);opacity:0}88.5%{transform:translateX(18px);opacity:1}"
        "89.5%{transform:translateX(-12px);opacity:1}90.5%{transform:translateX(7px);opacity:1}91%{transform:translateX(0);opacity:0}}"
        "@keyframes hum{0%,100%{opacity:1}48%{opacity:.93}50%{opacity:.78}52%{opacity:.95}}"
        ".gA{animation:gA 5s steps(1) infinite;mix-blend-mode:screen}"
        ".gB{animation:gB 5s steps(1) infinite;mix-blend-mode:screen}"
        ".sl{animation:slice 5s steps(1) infinite}"
        ".hum{animation:hum 2.4s linear infinite}"
    )
    svg.defs.append(
        f'<clipPath id="band1"><rect x="0" y="{ty - 44}" width="{W}" height="9"/></clipPath>'
        f'<clipPath id="band2"><rect x="0" y="{ty - 18}" width="{W}" height="6"/></clipPath>'
    )
    glyphs = lambda col, extra="": svg.text(title, cx, ty, ts, DISPLAY, col, "middle", 10 * ts / 74, extra)  # noqa: E731
    svg.add(
        f'<g class="gA">{glyphs(MAGENTA)}</g>',
        f'<g class="gB">{glyphs(CYAN)}</g>',
        f'<g class="hum" filter="url(#glow)">{glyphs(GREEN)}</g>',
        f'<g clip-path="url(#band1)"><g class="sl">{glyphs(HOT)}</g></g>',
        f'<g clip-path="url(#band2)"><g class="sl" style="animation-delay:-.15s">{glyphs(MAGENTA)}</g></g>',
    )

    # subtitle with a dark outline so it stays readable over the sun
    sub = f'//  {me["name"].upper()}  //'
    ss = fit(MONO, sub, 18, W - 48, 3)
    svg.add(svg.text(sub, cx, 160, ss, MONO, HOT, "middle", 3,
                     f'stroke="{BG}" stroke-width="{6 * 1000 / ss:.0f}" paint-order="stroke" stroke-linejoin="round"'))

    # HUD corners
    svg.add(
        svg.text("> NEO_PROTOCOL v1.7", 22, 30, 18 if W > NARROW else 16, CRT, DIM, spacing=1),
        svg.text("LINK: STABLE", W - 22, 30, 18 if W > NARROW else 16, CRT, DIM, "end", 1),
    )

    # access banner on the floor
    banner = "[ SYSTEM INITIALIZED ] :: ACCESS GRANTED"
    bs = fit(CRT, banner, 24, W - 84, 1.5)
    tw = CRT.width(banner, bs, 1.5)
    bw = tw + 52
    svg.styles.append("@keyframes blink{0%,49%{opacity:1}50%,100%{opacity:0}}.blink{animation:blink 1.06s steps(1) infinite}")
    svg.add(
        f'<rect x="{cx - bw / 2:.1f}" y="244" width="{bw:.1f}" height="34" rx="3" fill="{BG}" fill-opacity=".9" stroke="{GREEN}" stroke-opacity=".7"/>',
        svg.text(banner, cx - 9, 268, bs, CRT, GREEN, "middle", 1.5, 'filter="url(#glow)"'),
        f'<rect class="blink" x="{cx - 9 + tw / 2 + 6:.1f}" y="252" width="9" height="18" fill="{GREEN}"/>',
    )
    svg.add(f'<rect width="{W}" height="{H}" fill="url(#scan)"/>', f'<rect width="{W}" height="{H}" fill="url(#vig)"/>')
    refresh_beam(svg)
    svg.add("</g>", f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="10" fill="none" stroke="{LINE}"/>')
    return svg


# ── BOOT LOG ─────────────────────────────────────────────────────────────────
def boot(p: dict, W: int = W) -> SVG:
    narrow = W <= NARROW
    rows = [tuple(r) for r in p["boot"]] + [("ACCESS GRANTED", "")]
    lh = 24 if narrow else 27
    H = 66 + len(rows) * lh + 12
    svg = SVG(W, H, "Boot sequence",
              "Terminal boot log: " + "; ".join(f"{a} {b}".strip() for a, b in rows))
    crt_defs(svg)
    frame(svg, "skor17@zion: ~/boot.log", "TTY1")

    size, x0, y0 = (13 if narrow else 16), 28, 70
    cw = MONO.width("M", size)
    # column where "[ OK ]" starts
    status_col = max(len(f"> {m} ") for m, st in rows if st) + 4 if narrow else 52
    cycle = 12.0
    t, typed = 0.4, []
    css = []
    for i, (msg, status) in enumerate(rows):
        last = i == len(rows) - 1
        y = y0 + i * lh
        if status:
            dots = max(3, status_col - len(f"> {msg} ") - 1)
            line = f"> {msg} " + "." * dots + " "
        else:
            line = f"> {msg}" + ("" if last else "...")
        chars = len(line) + (6 if status else 0)
        # the last line is drawn bigger: slide the cover by its real width
        reveal = MONO.width(line, size + 2, 1) + cw if last else chars * cw
        dur = chars * 0.018
        s, e = t / cycle * 100, (t + dur) / cycle * 100
        t += dur + (0.45 if status else 0.25)
        # cover slides right in character steps -> typing effect
        css.append(
            f"@keyframes ty{i}{{0%,{s:.2f}%{{transform:translateX(0);animation-timing-function:steps({chars},end)}}"
            f"{e:.2f}%,99.5%{{transform:translateX({reveal:.1f}px)}}100%{{transform:translateX(0)}}}}"
            f".ty{i}{{animation:ty{i} {cycle}s infinite}}"
            f"@keyframes cu{i}{{0%,{s - 0.01:.2f}%{{opacity:0}}{s:.2f}%,{e:.2f}%{{opacity:1}}"
            f"{e + 0.01:.2f}%,100%{{opacity:{1 if last else 0}}}}}"
            f".cu{i}{{animation:cu{i} {cycle}s steps(1) infinite}}"
        )
        if last:
            typed.append(svg.text(line, x0, y, size + 2, MONO, HOT, spacing=1, attrs='filter="url(#glow)"'))
        else:
            typed.append(svg.text(line, x0, y, size, MONO, MID))
        if status:
            typed.append(svg.text("[", x0 + len(line) * cw, y, size, MONO, DIM)
                         + svg.text(status, x0 + (len(line) + 1.5) * cw, y, size, MONO, GREEN, attrs='filter="url(#glow)"')
                         + svg.text("]", x0 + (len(line) + 4.5) * cw, y, size, MONO, DIM))
        cursor = f'<g class="blink"><rect x="0" y="{y - size * .875:.1f}" width="{cw:.1f}" height="{size * 1.06:.1f}" fill="{GREEN}"/></g>' if last else \
            f'<rect x="0" y="{y - size * .875:.1f}" width="{cw:.1f}" height="{size * 1.06:.1f}" fill="{GREEN}"/>'
        typed.append(
            f'<g transform="translate({x0} 0)"><g class="ty{i}">'
            f'<rect x="0" y="{y - 19}" width="{W}" height="{lh}" fill="{BG}"/>'
            f'<g class="cu{i}">{cursor}</g></g></g>'
        )
    svg.styles.append("".join(css))
    svg.styles.append("@keyframes blink{0%,49%{opacity:1}50%,100%{opacity:0}}.blink{animation:blink 1.06s steps(1) infinite}")
    svg.add(f'<g clip-path="url(#bootclip)">', *typed, "</g>")
    svg.defs.append(f'<clipPath id="bootclip"><rect x="{x0 - 4}" y="40" width="{W - (2 * x0 - 8 if narrow else 260 + x0)}" height="{H - 44}"/></clipPath>')
    if narrow:  # no room for the oscilloscope
        overlay(svg)
        refresh_beam(svg)
        return svg

    # oscilloscope on the right
    ox, oy, ow, oh = W - 236, 52, 212, H - 70
    svg.add(f'<rect x="{ox}" y="{oy}" width="{ow}" height="{oh}" rx="4" fill="{PANEL}" stroke="{LINE}"/>')
    for gx in range(1, 6):
        svg.add(f'<line x1="{ox + gx * ow / 6:.1f}" y1="{oy}" x2="{ox + gx * ow / 6:.1f}" y2="{oy + oh}" stroke="{LINE}" stroke-dasharray="2 3"/>')
    for gy in range(1, 4):
        svg.add(f'<line x1="{ox}" y1="{oy + gy * oh / 4:.1f}" x2="{ox + ow}" y2="{oy + gy * oh / 4:.1f}" stroke="{LINE}" stroke-dasharray="2 3"/>')
    mid = oy + oh / 2 + 6
    pts = " ".join(f"{x:.0f},{mid + math.sin(x / 13) * 20 * math.sin(x / 71) + math.sin(x / 4.3) * 3:.1f}"
                   for x in range(0, 2 * 446 + 1, 3))
    svg.defs.append(f'<clipPath id="scope"><rect x="{ox + 1}" y="{oy + 1}" width="{ow - 2}" height="{oh - 2}"/></clipPath>')
    svg.styles.append("@keyframes scope{from{transform:translateX(0)}to{transform:translateX(-446px)}}.scope{animation:scope 4s linear infinite}")
    svg.add(
        f'<g clip-path="url(#scope)"><g transform="translate({ox} 0)"><g class="scope">'
        f'<polyline points="{pts}" fill="none" stroke="{GREEN}" stroke-width="1.6" filter="url(#glow)"/></g></g></g>',
        svg.text("UPLINK", ox + 10, oy + 20, 18, CRT, DIM, spacing=1),
        svg.text("98.6%", ox + ow - 10, oy + 20, 18, CRT, GREEN, "end", 1),
        svg.text(f'{p["identity"]["handle"]} > ZION', ox + 10, oy + oh - 10, 18, CRT, DIM, spacing=1),
    )
    overlay(svg)
    refresh_beam(svg)
    return svg


# ── WHOAMI ───────────────────────────────────────────────────────────────────
def section_title(svg: SVG, label: str, x: float, y: float, width: float) -> None:
    svg.add(
        f'<path d="M{x} {y - 11} l8 5.5 l-8 5.5 z" fill="{GREEN}"/>',
        svg.text(label, x + 16, y, 16, MONO, GREEN, spacing=2.5, attrs='filter="url(#glow)"'),
        f'<line x1="{x}" y1="{y + 11}" x2="{x + width}" y2="{y + 11}" stroke="{LINE}"/>',
    )


def whoami(p: dict, W: int = W) -> SVG:
    narrow = W <= NARROW
    rows = [tuple(r) for r in p["profile"]]
    lx, top = 28, 70
    # narrow: FOCUS goes below PROFILE instead of beside it
    rx, ftop = (lx, top + 42 + len(rows) * 32 + 18) if narrow else (452, top)
    H = max(top + 42 + (len(rows) - 1) * 32, ftop + 42 + (len(p["focus"]) - 1) * 32) + 28
    svg = SVG(W, H, "whoami",
              "PROFILE — " + ", ".join(f"{k}: {v}" for k, v in rows) + ". FOCUS — " + "; ".join(p["focus"]))
    crt_defs(svg)
    frame(svg, "skor17@zion: ~$ whoami", "UID 1017")
    section_title(svg, "PROFILE", lx, top, W - 2 * lx if narrow else 396)
    for i, (k, v) in enumerate(rows):
        y = top + 42 + i * 32
        svg.add(svg.text(k, lx, y, 15, MONO, DIM, spacing=1.5), svg.text(v, lx + 112, y, 16, MONO, HOT))
    section_title(svg, "FOCUS", rx, ftop, W - rx - 28)
    svg.styles.append("@keyframes led{0%,100%{opacity:1}50%{opacity:.35}}.led{animation:led 2s ease-in-out infinite}")
    for i, f in enumerate(p["focus"]):
        y = ftop + 42 + i * 32
        svg.add(
            f'<rect x="{rx}" y="{y - 11}" width="10" height="10" fill="none" stroke="{GREEN}"/>',
            f'<rect class="led" style="animation-delay:{-i * 0.5}s" x="{rx + 2.5}" y="{y - 8.5}" width="5" height="5" fill="{GREEN}"/>',
            svg.text(f, rx + 22, y, 15, MONO, HOT),
        )
    overlay(svg)
    refresh_beam(svg)
    return svg


# ── COMMS: spoken languages + system monitor ─────────────────────────────────
def comms(p: dict, W: int = W) -> SVG:
    narrow = W <= NARROW
    spoken = [tuple(s) for s in p["spoken"]]
    lx, top = 28, 70
    lw = W - 2 * lx if narrow else 380
    # narrow: the system monitor goes below the languages instead of beside them
    mx, mtop = (lx, top + 50 + len(spoken) * 54 + 6) if narrow else (450, top)
    H = max(286, mtop + 216)
    svg = SVG(W, H, "Languages and system monitor",
              "LANGUAGES — " + ", ".join(name.title() for name, _ in spoken) + ". Decorative system monitor.")
    crt_defs(svg)
    frame(svg, "skor17@zion: ~$ locale --human && htop", "LIVE")
    section_title(svg, "LANGUAGES", lx, top, lw)
    # every language gets the same idle "voice signal": decoration, not a proficiency meter
    svg.styles.append(
        "@keyframes eq{0%,100%{transform:scaleY(.25)}50%{transform:scaleY(1)}}"
        ".eq{animation:eq 1.1s ease-in-out infinite;transform-box:fill-box;transform-origin:center bottom}"
    )
    rnd = random.Random(3)
    bars, bw_, bgap = 14, 5, 4
    for i, (name, code) in enumerate(spoken):
        y = top + 50 + i * 54
        svg.add(
            f'<rect x="{lx}" y="{y - 11}" width="10" height="10" fill="none" stroke="{GREEN}"/>',
            f'<rect class="led" style="animation-delay:{-i * 0.5}s" x="{lx + 2.5}" y="{y - 8.5}" width="5" height="5" fill="{GREEN}"/>',
            svg.text(name, lx + 22, y, 17, MONO, HOT, spacing=2),
            svg.text(f"[{code}]", lx + lw, y, 15, MONO, DIM, "end", 1),
        )
        ex = lx + 170
        for j in range(bars):
            svg.add(f'<rect class="eq" style="animation-delay:{-rnd.uniform(0, 1.1):.2f}s;animation-duration:{rnd.uniform(.8, 1.5):.2f}s" '
                    f'x="{ex + j * (bw_ + bgap)}" y="{y - 14}" width="{bw_}" height="14" fill="{MID}"/>')
        svg.add(f'<line x1="{lx}" y1="{y + 16}" x2="{lx + lw}" y2="{y + 16}" stroke="{LINE}" stroke-dasharray="1 5"/>')
    svg.styles.append("@keyframes led{0%,100%{opacity:1}50%{opacity:.35}}.led{animation:led 2s ease-in-out infinite}")

    # system monitor
    mw = W - mx - 28
    section_title(svg, "SYSTEM MONITOR", mx, mtop, mw)
    svg.styles.append(
        "@keyframes cpu{0%{transform:scaleX(.42)}20%{transform:scaleX(.71)}40%{transform:scaleX(.36)}"
        "60%{transform:scaleX(.88)}80%{transform:scaleX(.55)}100%{transform:scaleX(.42)}}"
        "@keyframes ram{0%,100%{transform:scaleX(.64)}50%{transform:scaleX(.7)}}"
        ".cpu{animation:cpu 4s ease-in-out infinite;transform-box:fill-box;transform-origin:left center}"
        ".ram{animation:ram 6s ease-in-out infinite;transform-box:fill-box;transform-origin:left center}"
    )
    bw = mw - 128
    for i, (lbl, cls, load) in enumerate((("CPU", "cpu", "LOAD 0.42"), ("RAM", "ram", "6.6/10G"))):
        y = mtop + 40 + i * 28
        svg.add(
            svg.text(lbl, mx, y, 15, MONO, DIM, spacing=1.5),
            svg.text(load, mx + mw, y, 12, MONO, MID, "end"),
            f'<rect x="{mx + 50}" y="{y - 11}" width="{bw}" height="12" fill="none" stroke="{LINE}"/>',
            f'<rect class="{cls}" x="{mx + 52}" y="{y - 9}" width="{bw - 4}" height="8" fill="{GREEN}"/>',
        )
    procs = [("1024", "python3", "architect.py", "34"), ("2048", "oracle", "--predict", "22"),
             ("3072", "sentinel", "--patrol", "12"), ("4096", "agent.smith", "--replicate", "18"),
             ("5120", "git", "push origin", "4")]
    ty = mtop + 104
    cols = (0, 52, 150, mw)
    for j, h in enumerate(("PID", "PROCESS", "ARGS", "CPU%")):
        svg.add(svg.text(h, mx + cols[j], ty, 13, MONO, DIM, "end" if j == 3 else "start", 1))
    for i, row in enumerate(procs):
        y = ty + 20 + i * 18
        for j, v in enumerate(row):
            svg.add(svg.text(v, mx + cols[j], y, 13, MONO, HOT if j == 1 else MID, "end" if j == 3 else "start"))
    svg.styles.append("@keyframes sel{0%{transform:translateY(0)}20%{transform:translateY(18px)}40%{transform:translateY(36px)}"
                      "60%{transform:translateY(54px)}80%{transform:translateY(72px)}100%{transform:translateY(0)}}"
                      ".sel{animation:sel 7.5s steps(1) infinite}")
    svg.add(f'<g class="sel"><rect x="{mx - 4}" y="{ty + 6}" width="{mw + 8}" height="18" fill="{GREEN}" opacity=".12"/></g>')
    overlay(svg)
    refresh_beam(svg)
    return svg


# ── TECH STACK ───────────────────────────────────────────────────────────────
def stack(p: dict, W: int = W) -> SVG:
    narrow = W <= NARROW
    cats = p["stack"]
    # narrow: each category label sits on its own line above its chips
    lx, chip_x0, top = 28, (28 if narrow else 226), 70
    size, pad, ch_h, gap = 14, 10, 24, 8
    # lay out chips first to know the height
    rows, y = [], top
    for cat, items in cats.items():
        if narrow:
            y += 22
        x = chip_x0
        placed = []
        for it in items:
            w = MONO.width(it, size, 0.5) + pad * 2
            if x + w > W - 28:
                x = chip_x0
                y += ch_h + gap
            placed.append((it, x, y, w))
            x += w + gap
        rows.append((cat, placed, y))
        y += ch_h + 12
    H = y + 8
    svg = SVG(W, int(H), "Tech stack",
              "TECH STACK — " + "; ".join(f"{c}: {', '.join(i)}" for c, i in cats.items()))
    crt_defs(svg)
    frame(svg, "skor17@zion: ~$ ls ~/arsenal", f"{sum(len(v) for v in cats.values())} MODULES")
    svg.styles.append("@keyframes chip{0%,92%,100%{stroke:#0f3d1f}94%{stroke:#05ff62}}.chip{animation:chip 9s linear infinite}")
    k = 0
    for cat, placed, _ in rows:
        cy = placed[0][2]
        svg.add(svg.text("// " + cat, lx, cy - 8 if narrow else cy + 16.5, 14, MONO, DIM, spacing=1))
        for it, x, y, w in placed:
            svg.add(
                f'<rect class="chip" style="animation-delay:{k * 0.25:.2f}s" x="{x:.1f}" y="{y}" width="{w:.1f}" height="{ch_h}" rx="3" '
                f'fill="{PANEL}" stroke="{LINE}"/>',
                svg.text(it, x + pad, y + 16.5, size, MONO, GREEN, spacing=0.5),
            )
            k += 1
    overlay(svg)
    refresh_beam(svg)
    return svg


# ── FOOTER ───────────────────────────────────────────────────────────────────
def footer(p: dict, W: int = W) -> SVG:
    H = 96
    motto = p["identity"]["motto"]
    svg = SVG(W, H, motto, f"> {motto}  Wake up, Neo... follow the white rabbit.")
    crt_defs(svg)
    svg.add(f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="10" fill="{BG}" stroke="{LINE}"/>')
    digital_rain(svg, seed=99, height=H, cols=round(W / 16), size=14, opacity=0.22,
                 clip='clip-path="url(#fclip)"')
    svg.defs.append(f'<clipPath id="fclip"><rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="9"/></clipPath>')
    line = f"> {motto}"
    size = fit(MONO, line + " ", 20, W - 40)
    cw = MONO.width("M", size)
    n = len(line)
    x0 = W / 2 - n * cw / 2
    cycle = 9
    e = n * 0.06 / cycle * 100
    svg.styles.append(
        f"@keyframes ft{{0%{{transform:translateX(0);animation-timing-function:steps({n},end)}}{e:.2f}%,96%{{transform:translateX({n * cw:.1f}px)}}100%{{transform:translateX(0)}}}}"
        f".ft{{animation:ft {cycle}s infinite}}"
        "@keyframes blink{0%,49%{opacity:1}50%,100%{opacity:0}}.blink{animation:blink 1.06s steps(1) infinite}"
    )
    svg.add(
        svg.text(line, x0, 48, size, MONO, GREEN, spacing=0, attrs='filter="url(#glow)"'),
        f'<g transform="translate({x0:.1f} 0)"><g class="ft"><rect x="0" y="26" width="{n * cw + 40:.1f}" height="30" fill="{BG}"/>'
        f'<rect class="blink" x="2" y="31" width="{cw * 0.8:.1f}" height="21" fill="{GREEN}"/></g></g>',
        svg.text("WAKE UP, NEO...  FOLLOW THE WHITE RABBIT.", W / 2, 78,
                 fit(CRT, "WAKE UP, NEO...  FOLLOW THE WHITE RABBIT.", 18, W - 48, 2), CRT, DIM, "middle", 2),
    )
    overlay(svg)
    return svg


STATIC_CARDS = {
    "header": header,
    "boot": boot,
    "whoami": whoami,
    "comms": comms,
    "stack": stack,
    "footer": footer,
}
