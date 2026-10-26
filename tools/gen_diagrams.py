#!/usr/bin/env python3
"""Sinh bốn sơ đồ SVG động cho repo directadmin-php-tuning.

Vì sao có script này
--------------------
GitHub render Mermaid thành ảnh tĩnh và xoá thẻ <script> trong markdown. Muốn
"mũi tên di chuyển" thì phải là file SVG có CSS @keyframes và SMIL animateMotion
— trình duyệt chạy animation ngay cả khi SVG được nhúng qua <img>.

Sửa sơ đồ bằng cách sửa toạ độ/nội dung trong file này rồi chạy lại, đừng sửa
tay file .svg (lần chạy sau sẽ ghi đè).

Cách dùng
---------
    python3 tools/gen_diagrams.py            # ghi lại 4 file vào docs/img/
    python3 tools/gen_diagrams.py --check    # chỉ kiểm tra, exit 1 nếu lệch
    python3 tools/gen_diagrams.py --out DIR  # ghi ra thư mục khác

Script chỉ ghi vào thư mục đích, không sửa gì khác. Không cần thư viện ngoài.
"""
import argparse
import os
import sys
import xml.dom.minidom
from html import escape

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DEFAULT_OUT = os.path.join(REPO, "docs", "img")

OUT = DEFAULT_OUT
_PENDING = {}


def emit(name, parts):
    """Gom nội dung một sơ đồ lại; main() quyết định ghi hay chỉ so sánh."""
    _PENDING[name] = "\n".join(parts)

FONT = '"Segoe UI","Helvetica Neue",Arial,"Noto Sans",sans-serif'
MONO = '"SFMono-Regular",Consolas,"Liberation Mono",Menlo,monospace'

PALETTE = {
    "client":  ("#FFF7ED", "#F59E0B", "#7C2D12"),
    "web":     ("#EFF6FF", "#3B82F6", "#1E3A8A"),
    "php":     ("#F5F3FF", "#8B5CF6", "#4C1D95"),
    "data":    ("#ECFDF5", "#10B981", "#064E3B"),
    "cache":   ("#FEFCE8", "#EAB308", "#713F12"),
    "danger":  ("#FEF2F2", "#EF4444", "#7F1D1D"),
    "ok":      ("#F0FDF4", "#22C55E", "#14532D"),
    "neutral": ("#F8FAFC", "#94A3B8", "#0F172A"),
    "cmd":     ("#ECFEFF", "#0891B2", "#164E63"),
}

ARROW_COLORS = {
    "client": "#F59E0B", "web": "#3B82F6", "php": "#8B5CF6", "data": "#10B981",
    "cache": "#EAB308", "danger": "#EF4444", "ok": "#22C55E", "neutral": "#94A3B8",
    "cmd": "#0891B2",
}


def defs():
    marks = "".join(
        f'<marker id="ar-{k}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
        f'orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="{v}"/></marker>\n'
        for k, v in ARROW_COLORS.items()
    )
    return f"""  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#ffffff"/>
      <stop offset="1" stop-color="#f3f7fc"/>
    </linearGradient>
    <filter id="shadow" x="-20%" y="-20%" width="140%" height="150%">
      <feDropShadow dx="0" dy="2" stdDeviation="3.5" flood-color="#0f172a" flood-opacity="0.10"/>
    </filter>
    <filter id="glow" x="-90%" y="-90%" width="280%" height="280%">
      <feGaussianBlur stdDeviation="3" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
{marks}  </defs>
"""


STYLE = """
  <style>
    text { font-family: %(font)s; }
    .title { font-size: 22px; font-weight: 700; fill: #0b1220; }
    .sub   { font-size: 13.5px; fill: #64748b; }
    .n     { font-size: 16px; font-weight: 650; }
    .s     { font-size: 12.5px; fill: #64748b; }
    .mono  { font-family: %(mono)s; font-size: 13px; }
    .band  { font-size: 13px; font-weight: 700; letter-spacing: .2px; }

    .flow {
      fill: none; stroke-width: 2.8; stroke-linecap: round;
      stroke-dasharray: 2 12;
      animation: flow 1.15s linear infinite;
    }
    @keyframes flow { to { stroke-dashoffset: -28; } }

    .dashflow {
      fill: none; stroke-width: 2.2; stroke-dasharray: 8 7;
      animation: dashflow 1.7s linear infinite;
    }
    @keyframes dashflow { to { stroke-dashoffset: -30; } }

    .pulse { animation: pulse 2.8s ease-in-out infinite; }
    @keyframes pulse { 0%%,100%% { opacity: .35 } 50%% { opacity: .95 } }

    @media (prefers-reduced-motion: reduce) {
      .flow, .dashflow, .pulse { animation: none; }
    }
  </style>
""" % {"font": FONT, "mono": MONO}


def head(w, h, title, desc):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="t d">
  <title id="t">{escape(title)}</title>
  <desc id="d">{escape(desc)}</desc>
{defs()}{STYLE}
  <rect x="0" y="0" width="{w}" height="{h}" rx="18" fill="url(#bg)"/>
  <rect x="0.5" y="0.5" width="{w-1}" height="{h-1}" rx="18" fill="none" stroke="#e2e8f0"/>
'''


def card(x, y, w, h, kind, lines, fs=16, rx=13, shadow=True, mono_first=False, dash=False):
    fill, stroke, text = PALETTE[kind]
    cx = x + w / 2
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" '
           f'stroke-width="1.8"' + (' stroke-dasharray="7 5"' if dash else '') +
           (' filter="url(#shadow)"' if shadow else '') + '/>']
    n = len(lines)
    base = y + h / 2 - (n - 1) * 10 + 4
    for i, ln in enumerate(lines):
        cls = "mono" if (mono_first and i == 0) else ("n" if i == 0 else "s")
        size = fs if i == 0 else 12.5
        out.append(f'<text x="{cx}" y="{base + i * (size + 7):.1f}" text-anchor="middle" class="{cls}" '
                   f'fill="{text}"' + (f' style="font-size:{size}px"' if i else '') + f'>{escape(ln)}</text>')
    return "\n".join(out)


def cylinder(x, y, w, h, kind, lines):
    fill, stroke, text = PALETTE[kind]
    r = 15
    cx = x + w / 2
    out = [
        f'<path d="M{x} {y+r} a{w/2} {r} 0 0 1 {w} 0 v{h-2*r} a{w/2} {r} 0 0 1 -{w} 0 z" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="1.8" filter="url(#shadow)"/>',
        f'<ellipse cx="{cx}" cy="{y+r}" rx="{w/2}" ry="{r}" fill="#ffffff" fill-opacity="0.55" '
        f'stroke="{stroke}" stroke-width="1.8"/>',
    ]
    base = y + h / 2 + 2
    for i, ln in enumerate(lines):
        cls = "n" if i == 0 else "s"
        out.append(f'<text x="{cx}" y="{base + i * 20:.1f}" text-anchor="middle" class="{cls}" fill="{text}">'
                   f'{escape(ln)}</text>')
    return "\n".join(out)


def conn(d, kind, dots=1, dur=2.6, begin=0.0, delay=0.0, width=2.8, opacity=0.35):
    color = ARROW_COLORS[kind]
    parts = [f'<path d="{d}" fill="none" stroke="{color}" stroke-opacity="{opacity}" stroke-width="2" '
             f'marker-end="url(#ar-{kind})"/>',
             f'<path d="{d}" class="flow" stroke="{color}" style="animation-delay:-{delay}s"/>']
    for k in range(dots):
        b = begin + k * (dur / max(dots, 1))
        parts.append(f'<circle r="4.4" fill="{color}" filter="url(#glow)">'
                     f'<animateMotion dur="{dur}s" begin="{b:.2f}s" repeatCount="indefinite" path="{d}"/></circle>')
    return "\n".join(parts)


def label(x, y, text, anchor="middle", fill="#475569", size=12, weight=600, cls=""):
    return (f'<text x="{x}" y="{y}" text-anchor="{anchor}" fill="{fill}" '
            f'style="font-size:{size}px;font-weight:{weight}" class="{cls}">{escape(text)}</text>')


# ---------------------------------------------------------------------------
# 1. LUỒNG REQUEST  (1140 x 440)
# ---------------------------------------------------------------------------
W, H = 1140, 448
s = [head(W, H, "Luồng request trên DirectAdmin",
          "Người dùng, CDN, nginx, Apache, PHP-FPM, MySQL và Redis với mũi tên chuyển động theo chiều request.")]
s.append('<text x="36" y="52" class="title">Luồng request trên DirectAdmin</text>')
s.append('<text x="36" y="80" class="sub">Mũi tên chuyển động theo chiều request · màu là vai trò của từng tầng</text>')

y0, hh = 172, 92
s.append(card(36, y0, 140, hh, "client", ["Người dùng", "trình duyệt"]))
s.append(card(216, y0, 140, hh, "client", ["CDN / WAF", "cache · lọc bot"]))
s.append(card(396, y0, 150, hh, "web", ["nginx", "static · 65s"]))
s.append(card(586, y0, 150, hh, "web", ["Apache", "nginx_apache · 65s"]))
s.append(card(776, y0, 160, hh, "php", ["PHP-FPM", "pool USER · 60s"]))
s.append(cylinder(976, 108, 134, 96, "data", ["MySQL", "query"]))
s.append(cylinder(976, 250, 134, 96, "data", ["Redis", "cache"]))
s.append(card(396, 342, 150, 76, "data", ["NVMe", "file tĩnh"]))

s.append(conn("M176 218 L212 218", "client", dur=2.0))
s.append(conn("M356 218 L392 218", "client", dur=2.0, begin=0.25))
s.append(conn("M546 218 L582 218", "web", dur=2.1, begin=0.1))
s.append(conn("M736 218 L772 218", "web", dur=2.1, begin=0.45))
s.append(conn("M936 204 C962 204 962 150 972 150", "php", dur=2.4, begin=0.15))
s.append(conn("M936 232 C962 232 962 286 972 286", "php", dur=2.4, begin=0.85))

s.append('<path d="M471 264 L471 338" fill="none" stroke="#10B981" stroke-opacity="0.35" stroke-width="2" '
         'stroke-dasharray="7 6" marker-end="url(#ar-data)"/>')
s.append('<path d="M471 264 L471 338" class="dashflow" stroke="#10B981" opacity="0.9"/>')
s.append(label(483, 306, "file tĩnh", anchor="start", fill="#0f766e"))


s.append(f'''
  <g>
    <rect x="36" y="352" width="330" height="62" rx="13" fill="#FFFFFF" stroke="#e2e8f0"/>
    <circle cx="58" cy="374" r="4.4" fill="#3B82F6" filter="url(#glow)"/>
    <text x="72" y="378" class="s" style="font-size:12px">gói tin di chuyển theo chiều request</text>
    <line x1="58" y1="396" x2="94" y2="396" stroke="#10B981" stroke-width="2" stroke-dasharray="6 5"/>
    <text x="104" y="400" class="s" style="font-size:12px">nét đứt = không đi qua PHP</text>
  </g>''')
s.append('</svg>')
emit("request-flow.svg", s)


# ---------------------------------------------------------------------------
# 2. CẤU HÌNH (1220 x 610)
# ---------------------------------------------------------------------------
W, H = 1220, 604
s = [head(W, H, "Cấu hình DirectAdmin: nguồn và kết quả",
          "Nguồn được sửa, lệnh da build biến đổi, kết quả sinh ra và có thể bị ghi đè.")]
s.append('<text x="36" y="52" class="title">Cấu hình: chỗ nào được sửa, chỗ nào bị ghi đè</text>')
s.append('<text x="36" y="80" class="sub">Sửa cột xanh thì bền qua rebuild · sửa cột đỏ thì lần build sau sẽ mất</text>')

s.append('<text x="36" y="118" class="band" fill="#15803d">● NGUỒN — sửa ở đây · bền qua rebuild</text>')
s.append('<text x="500" y="118" class="band" fill="#0e7490">● LỆNH</text>')
s.append('<text x="960" y="118" class="band" fill="#b91c1c">● KẾT QUẢ — đừng sửa</text>')

sources = [
    (30,  "php.conf.d/99-*.ini", "drop-in"),
    (262, "options.conf", "bản · handler"),
    (494, "templates/custom/", "template riêng"),
    (726, "CUSTOM1 / CUSTOM2", "giao diện DA"),
    (958, "custom/opcache/", "opcache.ini"),
]
for x, a, b in sources:
    s.append(card(x, 136, 210, 60, "ok", [a, b], fs=15, mono_first=True))

cmds = [
    (196, 236, ["da build php", "biên dịch · ghi php.ini"], 64, 276),
    (486, 264, ["da build rewrite_confs", "sinh lại vhost và pool"], 64, 276),
    (806, 230, ["da build opcache", "cấu hình OPcache", "→ 10-directadmin.ini"], 78, 269),
]
for x, w, lines, h, y in cmds:
    s.append(card(x, y, w, h, "cmd", lines, fs=15, mono_first=True))

outs = [
    (48, 250, "php.ini", "file chính"),
    (320, 250, "10-directadmin.ini", "CustomBuild sinh"),
    (600, 250, "php-fpm83.conf", "pool theo user"),
    (880, 300, "vhost nginx / httpd", "cấu hình web"),
]
for x, w, a, b in outs:
    s.append(card(x, 440, w, 64, "danger", [a, b], fs=15, mono_first=True))

# fan-in (sửa -> lệnh)
s.append(conn("M150 196 C150 230 260 240 280 272", "ok", dur=2.8))
s.append(conn("M330 196 C300 226 300 244 300 272", "ok", dur=2.4, begin=0.6))
s.append(conn("M365 196 C380 224 470 238 530 272", "ok", dur=3.0, begin=0.3))
s.append(conn("M610 196 C610 226 610 244 610 272", "ok", dur=2.2, begin=0.9))
s.append(conn("M830 196 C800 226 730 244 690 272", "ok", dur=2.8, begin=1.3))
s.append(conn("M1063 196 C1063 226 980 244 940 272", "ok", dur=2.6, begin=1.0))

# fan-out (lệnh -> kết quả)
s.append(conn("M280 340 C280 378 210 402 180 436", "cmd", dur=2.8))
s.append(conn("M320 340 C320 378 400 402 420 436", "cmd", dur=2.8, begin=0.8))
s.append(conn("M600 340 C600 378 690 400 720 436", "cmd", dur=2.6, begin=0.4))
s.append(conn("M720 340 C780 378 970 402 1010 436", "cmd", dur=3.0, begin=1.1))

s.append(f'''
  <g>
    <rect x="872" y="522" width="316" height="50" rx="12" fill="#FEF2F2" stroke="#FCA5A5" stroke-dasharray="6 5"/>
    <text x="890" y="544" class="s" fill="#B91C1C" style="font-size:12.5px">⚠ Bị ghi đè mỗi lần da build</text>
    <text x="890" y="562" class="s" fill="#DC2626" style="font-size:11.5px">Muốn bền: sửa custom/ hoặc 99-*.ini</text>
  </g>''')
s.append('</svg>')
emit("config-pipeline.svg", s)


# ---------------------------------------------------------------------------
# 3. POOL PHP-FPM (1140 x 640)
# ---------------------------------------------------------------------------
W, H = 1160, 636
s = [head(W, H, "Pool PHP-FPM theo user trên DirectAdmin",
          "Một master cho mỗi phiên bản PHP, mỗi user một pool, worker sinh theo nhu cầu.")]
s.append('<text x="36" y="52" class="title">Một pool cho mỗi user — không phải mỗi domain</text>')
s.append('<text x="36" y="80" class="sub">Mọi domain của cùng một tài khoản chia nhau đúng pm.max_children của user đó</text>')

s.append(card(430, 108, 280, 66, "web", ["nginx / Apache", "gửi request qua socket"]))
s.append(card(400, 216, 340, 68, "cache", ["Master php-fpm83", "một vùng OPcache cho mọi pool"]))
s.append(card(790, 216, 250, 68, "neutral", ["OPcache 256 MB", "dùng chung mọi pool"], shadow=False))

s.append(conn("M570 174 L570 212", "web", dur=1.9))
s.append('<path d="M740 250 L786 250" fill="none" stroke="#EAB308" stroke-opacity="0.4" stroke-width="2" '
         'stroke-dasharray="7 6" marker-end="url(#ar-cache)"/>')
s.append('<path d="M740 250 L786 250" class="dashflow" stroke="#EAB308" opacity="0.95"/>')

pools = [
    (30,  "Pool alice", "max_children = 4", 4, "ok", False),
    (425, "Pool bob", "max_children = 4", 4, "php", False),
    (820, "Pool carol", "max_children = 12", 4, "danger", True),
]
for x, name, sub, chips, kind, busy in pools:
    fill, stroke, text = PALETTE[kind]
    if busy:
        s.append(f'<rect x="{x-5}" y="338" width="310" height="198" rx="19" fill="#FEE2E2" '
                 f'opacity="0.7" class="pulse"/>')
    s.append(f'<rect x="{x}" y="342" width="300" height="190" rx="16" fill="{fill}" stroke="{stroke}" '
             f'stroke-width="1.8" filter="url(#shadow)"/>')
    s.append(f'<text x="{x+150}" y="374" text-anchor="middle" class="n" fill="{text}">{escape(name)}</text>')
    s.append(f'<text x="{x+150}" y="398" text-anchor="middle" class="s">{escape(sub)}</text>')

    for i in range(chips):
        cx0 = x + 24 + i * 66
        s.append(f'<rect x="{cx0}" y="416" width="54" height="34" rx="9" fill="#ffffff" stroke="{stroke}" stroke-width="1.2"/>')
        s.append(f'<circle cx="{cx0+27}" cy="433" r="5.6" fill="{stroke}" opacity="0.85">'
                 f'<animate attributeName="opacity" values="0.3;1;0.3" dur="2.4s" begin="{i*0.28}s" repeatCount="indefinite"/></circle>')

    if busy:
        s.append(f'<text x="{x+150}" y="478" text-anchor="middle" class="s" fill="#B91C1C">+ 8 worker · đang quá tải</text>')
    else:
        s.append(f'<text x="{x+150}" y="478" text-anchor="middle" class="s">ondemand · 0 worker khi rảnh</text>')
    s.append(f'<text x="{x+150}" y="504" text-anchor="middle" class="s" style="font-size:11px">/usr/local/php83/sockets/USER.sock</text>')

s.append(conn("M470 284 C470 312 240 312 180 338", "cache", dur=2.9))
s.append(conn("M570 284 L570 338", "cache", dur=2.3, begin=0.5))
s.append(conn("M670 284 C670 312 910 312 970 338", "cache", dur=2.9, begin=1.0))

s.append(f'''
  <g>
    <rect x="36" y="556" width="1068" height="58" rx="14" fill="#FFFBEB" stroke="#FCD34D" stroke-dasharray="7 5"/>
    <text x="56" y="580" class="s" fill="#92400E" style="font-size:12.5px">Một site bị crawl có thể làm nghẽn cả tài khoản: 12 domain của alice chia nhau 4 worker.</text>
    <text x="56" y="600" class="s" fill="#92400E" style="font-size:12.5px">Cách ly theo domain: tách tài khoản, hoặc bật isolated FPM (mỗi user một master, ~20 MB khi rảnh).</text>
  </g>''')
s.append('</svg>')
emit("fpm-pools.svg", s)


# ---------------------------------------------------------------------------
# 4. CHUỖI TIMEOUT (940 x 520)
# ---------------------------------------------------------------------------
W, H = 940, 524
s = [head(W, H, "Chuỗi timeout lồng nhau",
          "nginx, Apache, PHP-FPM và PHP với các mốc thời gian lồng vào nhau.")]
s.append('<text x="36" y="52" class="title">Timeout lồng nhau: tầng ngoài phải chậm hơn</text>')
s.append('<text x="36" y="80" class="sub">Nếu nginx cắt trước, người dùng thấy 504 còn PHP vẫn chạy và vẫn chiếm worker</text>')

levels = [
    (40, 112, 860, 336, "nginx", "proxy_read_timeout 65s", "#3B82F6", "#EFF6FF", 2.4),
    (80, 150, 780, 260, "Apache", "ProxyTimeout 65s", "#0891B2", "#ECFEFF", 2.9),
    (120, 188, 700, 184, "PHP-FPM", "request_terminate_timeout 60s", "#8B5CF6", "#F5F3FF", 3.4),
    (160, 226, 620, 108, "PHP", "max_execution_time 60s", "#EAB308", "#FEFCE8", 3.9),
]
for x, y, w, h, name, val, color, fill, dur in levels:
    s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="16" fill="{fill}" fill-opacity="0.5" '
             f'stroke="{color}" stroke-width="2" stroke-dasharray="9 7" class="dashflow" '
             f'style="animation-duration:{dur}s"/>')
    s.append(f'<text x="{x+18}" y="{y+27}" class="band" fill="{color}">{name}</text>')
    s.append(f'<text x="{x+w-18}" y="{y+27}" text-anchor="end" class="mono" fill="{color}" '
             f'style="font-size:11.5px">{escape(val)}</text>')

s.append('<rect x="300" y="264" width="340" height="54" rx="13" fill="#ffffff" stroke="#22C55E" '
         'stroke-width="2" filter="url(#shadow)"/>')
s.append('<text x="470" y="288" text-anchor="middle" class="n" fill="#14532D">Ứng dụng</text>')
s.append('<text x="470" y="307" text-anchor="middle" class="s" style="font-size:11.5px">query · render · gọi API</text>')

for i, (x, y, w, h, *_) in enumerate(levels):
    d = f"M{x+22} {y} H{x+w-22} V{y+h} H{x+22} Z"
    s.append(f'<circle r="3.8" fill="#0F172A" opacity="0.5"><animateMotion dur="{10+i*1.8}s" '
             f'repeatCount="indefinite" path="{d}"/></circle>')

s.append(f'''
  <g>
    <rect x="40" y="466" width="860" height="34" rx="10" fill="#F8FAFC" stroke="#E2E8F0"/>
    <text x="58" y="488" class="s" style="font-size:12px">65s &gt; 60s &gt; thời gian xử lý thật — mỗi lớp rộng hơn lớp trong ít nhất 5 giây để tránh cắt oan.</text>
  </g>''')
s.append('</svg>')
emit("timeouts.svg", s)



def main(argv=None):
    ap = argparse.ArgumentParser(description="Sinh / kiểm tra bốn sơ đồ SVG động.")
    ap.add_argument("--out", default=DEFAULT_OUT, help="thư mục đích (mặc định: docs/img/)")
    ap.add_argument("--check", action="store_true",
                    help="không ghi file; exit 1 nếu file đã commit khác bản sinh ra")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    # Sinh xong mới ghi: sai XML thì không làm hỏng file đang có.
    for name, body in _PENDING.items():
        try:
            xml.dom.minidom.parseString(body)
        except Exception as exc:  # noqa: BLE001
            print(f"lỗi: {name} không phải XML hợp lệ: {exc}", file=sys.stderr)
            return 2

    if args.check:
        drift = []
        for name in sorted(_PENDING):
            path = os.path.join(args.out, name)
            if not os.path.exists(path):
                drift.append(f"thiếu file: {path}")
                continue
            with open(path, encoding="utf-8") as fh:
                if fh.read() != _PENDING[name]:
                    drift.append(f"lệch nội dung: {path}")
        if drift:
            print("Sơ đồ chưa đồng bộ với script:", file=sys.stderr)
            for line in drift:
                print("  - " + line, file=sys.stderr)
            print("Chạy: python3 tools/gen_diagrams.py", file=sys.stderr)
            return 1
        if not args.quiet:
            print(f"OK: {len(_PENDING)} sơ đồ khớp với script")
        return 0

    os.makedirs(args.out, exist_ok=True)
    for name in sorted(_PENDING):
        path = os.path.join(args.out, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(_PENDING[name])
        if not args.quiet:
            print(f"ghi {path} ({os.path.getsize(path)} B)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
