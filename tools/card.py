#!/usr/bin/env python3
"""Draw recipe model cards (docs/card.png) from kindling.json.

  python3 tools/card.py                             redraw docs/card.png for every non-external recipe
  python3 tools/card.py DIR [DIR ...]               redraw docs/card.png for the listed recipe folder(s)
  python3 tools/card.py --check [DIR ...]           verify docs/card.png matches kindling.json; exit 1 if stale
  python3 tools/card.py --dry-run [DIR ...]         render in memory to validate, writing nothing
  python3 tools/card.py KINDLING.json [--config ID | --all] [--out card.png | card.gif] [--width 800] [--light]

Ported from kindlingai/gr8's bench/gif.py card subcommand so cards draw standalone in kindlingai/recipes with zero
dependency on a gr8 checkout. Uses bundled SIL OFL 1.1 fonts in tools/fonts/ (JetBrains Mono Regular and Space Grotesk
Bold; see tools/fonts/README.md) for deterministic rendering across platforms and CI.

Needs Pillow (pip install -r tools/requirements.txt).
"""
import argparse
import io
import json
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FONTS_DIR = Path(__file__).resolve().parent / 'fonts'
NOT_RECIPES = {'tools', 'schema', 'cli', 'template'}


def _rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


# kindlingai.dev's colors, from https://kindlingai.dev/assets/brand.css (ink, paper, ember, flame core, ai text) and
# /styles.css (surface, surface-2, line, muted, meter-track), dark and light
THEMES = {
    'dark': {k: _rgb(v) for k, v in {
        'bg': '#16130F', 'surface': '#1E1A15', 'surface2': '#29241D', 'line': '#342E26', 'text': '#F2EDE4',
        'muted': '#A39A8C', 'track': '#2E2820', 'accent': '#FF6B1A', 'accent2': '#FFC24A', 'value': '#FFC24A'}.items()},
    'light': {k: _rgb(v) for k, v in {
        'bg': '#F2EDE4', 'surface': '#FBF8F3', 'surface2': '#EAE3D7', 'line': '#D9D0C2', 'text': '#16130F',
        'muted': '#6B6358', 'track': '#E4DCCF', 'accent': '#E8590C', 'accent2': '#FFB020', 'value': '#C2410C'}.items()},
}
GROUNDS = ('bg', 'surface')   # the fills text sits on: the palette ramps from each to every other color
RAMP = 4                      # palette steps from a fill to each color, for antialiased edges
PAD = 6
DECODE_ORDER = ('code', 'prose', 'structured')

FONTS = [
    str(FONTS_DIR / 'JetBrainsMono-Regular.ttf'),
    'JetBrainsMono-Regular.ttf',
    'JetBrainsMono[wght].ttf',
    '/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Regular.ttf',
    'DejaVuSansMono.ttf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',
    '/usr/share/fonts/TTF/DejaVuSansMono.ttf',
    '/usr/share/fonts/dejavu/DejaVuSansMono.ttf',
    '/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf',
    '/System/Library/Fonts/Menlo.ttc',
    '/System/Library/Fonts/Monaco.ttf',
    '/Library/Fonts/Courier New.ttf',
    'C:/Windows/Fonts/consola.ttf',
]
DISPLAY_FONTS = [
    str(FONTS_DIR / 'SpaceGrotesk-Bold.ttf'),
    'SpaceGrotesk-Bold.ttf',
    'SpaceGrotesk[wght].ttf',
    'SpaceGrotesk-Regular.ttf',
]


def pillow():
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        sys.exit('card.py: needs Pillow (pip install -r tools/requirements.txt)')
    return Image, ImageDraw, ImageFont


def char_width(c):
    return 2 if unicodedata.east_asian_width(c) in 'WF' else 1


class Painter:
    def __init__(self, font, cw):
        self.font, self.cw = font, cw
        self.mono = abs(font.getlength('i') - font.getlength('M')) < 0.01

    def line(self, draw, x, y, cells, colors):
        """cells: [(style, char)] at x, y on the character grid. ASCII runs of one style go in one call when the font
        is monospace; anything else goes a character at a time, at its cell."""
        col, i = 0, 0
        while i < len(cells):
            style, c = cells[i]
            if self.mono and c.isascii():
                j = i
                while j < len(cells) and cells[j][0] == style and cells[j][1].isascii():
                    j += 1
                run = ''.join(ch for _, ch in cells[i:j])
                draw.text((x + col * self.cw, y), run, font=self.font, fill=colors[style])
                col += j - i
                i = j
            else:
                draw.text((x + col * self.cw, y), c, font=self.font, fill=colors[style])
                col += char_width(c)
                i += 1

    def text(self, draw, x, y, s, color):
        self.line(draw, x, y, [('c', ch) for ch in s], {'c': color})


def palette(Image, theme):
    """A fixed palette: each fill in GROUNDS, then RAMP steps from it to every other color of the theme."""
    cols = []
    for g in GROUNDS:
        ground = theme[g]
        cols.append(ground)
        for c in dict.fromkeys(theme.values()):
            if c != ground:
                cols += [tuple(round(b + (v - b) * k / RAMP) for b, v in zip(ground, c)) for k in range(1, RAMP + 1)]
    cols = list(dict.fromkeys(cols))
    pal = Image.new('P', (1, 1))
    flat = [v for c in cols for v in c]
    pal.putpalette(flat + flat[:3] * (256 - len(cols)))
    return pal, len(cols)


def load_font(ImageFont, path, size, names=FONTS, fallback=True):
    """path, else the first of names that loads, else Pillow's default font, or None without fallback."""
    for p in ([path] if path else names):
        try:
            return ImageFont.truetype(p, size), p
        except OSError:
            if path:
                sys.exit(f'{path}: cannot load this font')
    if not fallback:
        return None, None
    try:
        return ImageFont.load_default(size), "Pillow's default"
    except TypeError:   # Pillow before 10.1: a fixed bitmap font
        return ImageFont.load_default(), "Pillow's default"


def cell(ImageFont, font_path, font_size):
    """-> (font, its name, cell width, line height in pixels)"""
    font, name = load_font(ImageFont, font_path, font_size)
    asc, desc = font.getmetrics() if hasattr(font, 'getmetrics') else (font_size, 2)
    return font, name, font.getlength('M'), asc + desc + 2


def num(v):
    return f'{v:,}' if isinstance(v, int) else f'{v:,.1f}'


def context_label(n):
    return f'{n // 1024}K' if n >= 1024 and n % 1024 == 0 else f'{n:,}'


def spaced_width(text, font, gap):
    if not text:
        return 0.0
    return sum(font.getlength(ch) for ch in text) + gap * (len(text) - 1)


def spaced(d, x, y, text, font, fill, gap):
    """Draw text a character at a time, gap pixels apart: the site's letter-spaced capitals. -> the width drawn"""
    x0 = x
    for ch in text:
        d.text((x, y), ch, font=font, fill=fill)
        x += font.getlength(ch) + gap
    return x - x0 - gap


def load_hardware():
    hw_path = ROOT / 'hardware.json'
    if hw_path.is_file():
        return json.loads(hw_path.read_text())
    return {}


def resolve_hardware(doc, kindling_path, hardware_map):
    if doc.get('hardware'):
        return str(doc['hardware'])
    try:
        rel = Path(kindling_path).resolve().parent.relative_to(ROOT).as_posix()
        parts = rel.split('/')
        if len(parts) == 4 and parts[1] in hardware_map:
            return hardware_map[parts[1]]['name']
    except ValueError:
        pass
    return None


def ordered_decode(dec):
    """Standard keys (code, prose, structured) first per schema/kindling.v1.json, then remaining keys in order."""
    items = []
    seen = set()
    for k in DECODE_ORDER:
        if k in dec and isinstance(dec[k], (int, float)):
            items.append((k, dec[k]))
            seen.add(k)
    for k, v in dec.items():
        if k not in seen and isinstance(v, (int, float)):
            items.append((k, v))
    return items


def card_rows(doc, c, hardware_label=None, title_split=False):
    """A config of a kindling.json as rows to draw, in theme color names.

    A row is ('title', text, right text), ('text', color, text), ('section', heading) or
    ('bar', label, value, section maximum, value text, section). Only fields present show.
    """
    nodes = c.get('nodes')
    right = ' · '.join(x for x in (c.get('label'), nodes and f"{nodes} node{'s' if nodes != 1 else ''}") if x)
    title_str = str(doc.get('title') or '')
    variant_str = str(doc.get('variant') or '')
    if title_split and variant_str:
        rows = [('title', title_str, right), ('text', 'text', variant_str)]
    else:
        combined = ' · '.join(x for x in (title_str, variant_str) if x)
        rows = [('title', combined, right)]

    if doc.get('model'):
        rows.append(('text', 'text', str(doc['model'])))
    hw = hardware_label or doc.get('hardware')
    if hw:
        rows.append(('text', 'muted', str(hw)))
    if doc.get('stack'):
        rows.append(('text', 'muted', ' · '.join(str(x) for x in doc['stack'])))

    def bars(heading, items):
        if items:
            rows.append(('section', heading))
            top = max(v for _, v, _ in items) or 1
            rows.extend(('bar', label, v, top, text, heading) for label, v, text in items)

    def prompts(key):
        r = c.get(key)
        if isinstance(r, list) and len(r) == 2 and all(isinstance(x, (int, float)) for x in r):
            return f', prompt {r[0]} tokens' if r[0] == r[1] else f', prompts {r[0]}-{r[1]} tokens'
        if isinstance(r, list) and len(r) == 1 and isinstance(r[0], (int, float)) and r[0] > 0:
            return f', prompt {r[0]} tokens'
        return ''

    dec = c.get('decode') or {}
    bars('Decode · tok/s, one stream' + prompts('decode_prompt_tokens'),
         [(w, v, num(v)) for w, v in ordered_decode(dec)])
    bars('Prefill · tok/s, cold prompt',
         [(context_label(x['context']), x['tps'], num(x['tps']))
          for x in c.get('prefill') or []
          if isinstance(x, dict) and 'context' in x and isinstance(x.get('tps'), (int, float))])

    def per_stream(x):
        v = next((x[k] for k in ('per_stream_tps', 'per_stream') if isinstance(x.get(k), (int, float))), None)
        each = f'  {num(v)} each' if v is not None else ''
        t = x.get('ttft_p50_s')
        return each + (f'  first token {t:.2f} s' if isinstance(t, (int, float)) else '')

    bars('Concurrency · total tok/s' + prompts('concurrency_prompt_tokens'),
         [(f"{x['streams']} stream{'s' if x['streams'] != 1 else ''}", x['aggregate_tps'],
           num(x['aggregate_tps']) + per_stream(x))
          for x in c.get('concurrency') or []
          if isinstance(x, dict) and 'streams' in x and isinstance(x.get('aggregate_tps'), (int, float))])

    limits = [f'{name} {num(c[k])}' for k, name in (
        ('max_context', 'max context'), ('kv_pool_tokens', 'KV pool'), ('max_concurrent', 'max concurrent'))
        if isinstance(c.get(k), (int, float))]
    per_chat = [f"{x['chats']} {'chat' if x['chats'] == 1 else 'chats'} {num(x['tokens'])}"
                + (f" ({x['source']})" if x.get('source') else '')
                for x in c.get('max_tokens_per_chat') or []
                if isinstance(x, dict) and 'chats' in x and 'tokens' in x]
    if c.get('max_tokens_per_chat_note'):
        per_chat.append(str(c['max_tokens_per_chat_note']))
    quality = [f"{q['name']}: {q['value']}" for q in c.get('quality') or []
               if isinstance(q, dict) and 'name' in q and 'value' in q]
    if limits or per_chat or quality:
        rows.append(('section', 'Limits' if (limits or per_chat) else 'Quality'))
        if limits:
            rows.append(('text', 'muted', ' · '.join(limits)))
        if per_chat:
            rows.append(('text', 'text', 'Max tokens per active chat: ' + ' · '.join(per_chat)))
        rows.extend(('text', 'text', q) for q in quality)
    return rows


def wrap_line(text, cols):
    """Word-wrap a single line that exceeds cols, without dropping characters."""
    if len(text) <= cols:
        return [text]
    lines = []
    cur = ''
    for word in text.split(' '):
        if not cur:
            while len(word) > cols:
                lines.append(word[:cols])
                word = word[cols:]
            cur = word
        elif len(cur) + 1 + len(word) <= cols:
            cur = f'{cur} {word}'
        else:
            lines.append(cur)
            while len(word) > cols:
                lines.append(word[:cols])
                word = word[cols:]
            cur = word
    if cur:
        lines.append(cur)
    return lines or ['']


def fit(rows, cols):
    """Text rows longer than cols split at ' · ' separators first, then word-wrap any remaining long lines."""
    out = []
    for row in rows:
        if row[0] != 'text' or len(row[2]) <= cols:
            out.append(row)
            continue
        line = ''
        for part in row[2].split(' · '):
            if line and len(line) + 3 + len(part) > cols:
                for wrapped in wrap_line(line, cols):
                    out.append(('text', row[1], wrapped))
                line = part
            else:
                line = f'{line} · {part}' if line else part
        for wrapped in wrap_line(line, cols):
            out.append(('text', row[1], wrapped))
    return out


def render_card_bytes(kindling_path, *, config=None, all_configs=False, across=1, width=800, light=False,
                      font_path=None, display_font_path=None, font_size=14, gif=False, fps=25.0, fill=1.2, hold=4.0,
                      hardware_map=None):
    """Render a card to PNG (or GIF) bytes. -> (bytes, summary_info_dict)"""
    Image, ImageDraw, ImageFont = pillow()
    theme = THEMES['light' if light else 'dark']
    doc = json.loads(Path(kindling_path).read_text())
    configs = doc.get('configs') or []
    if all_configs:
        chosen = configs
    else:
        want = config or doc.get('default_config') or (configs[0]['id'] if configs else None)
        chosen = [c for c in configs if c.get('id') == want]
        if not chosen:
            sys.exit(f"{kindling_path}: no config {want!r}; configs: {', '.join(c.get('id', '?') for c in configs)}")
    if not chosen:
        sys.exit(f'{kindling_path}: no configs')

    font, font_name, cw, lh = cell(ImageFont, font_path, font_size)
    head, head_name = load_font(ImageFont, display_font_path, font_size + 2, DISPLAY_FONTS, fallback=False)
    head = head or font
    title_gap = round(0.08 * head.size)
    paint = Painter(font, cw)
    pal, _ = palette(Image, theme)

    across = max(1, min(across, len(chosen)))
    gap = 2 * PAD
    cardw = (width - gap * (across - 1)) // across
    cols = int((cardw - 2 * PAD) // cw) - 4   # a border cell and a space on each side
    if cols < 30:
        sys.exit(f'--width {width} leaves {cols} characters a card: too narrow')

    hw_label = resolve_hardware(doc, kindling_path, hardware_map or {})
    layouts = []
    for c in chosen:
        rows = card_rows(doc, c, hardware_label=hw_label, title_split=False)
        # Split title and variant onto two lines if combined spaced title would collide with the right badge
        t_text, r_text = rows[0][1], rows[0][2]
        avail_px = (cols - len(r_text) - (2 if r_text else 0)) * cw
        if doc.get('variant') and spaced_width(t_text.upper(), head, title_gap) > avail_px:
            rows = card_rows(doc, c, hardware_label=hw_label, title_split=True)
        layouts.append(fit(rows, cols))

    # with several cards a section scales to its largest value on any of them, so the cards compare
    top = {}
    for row in (r for rows in layouts for r in rows if r[0] == 'bar'):
        top[row[5]] = max(top.get(row[5], 0), row[2])
    layouts = [[r[:3] + (top[r[5]] or 1,) + r[4:] if r[0] == 'bar' else r for r in rows] for rows in layouts]

    heights = [(len(rows) + 2) * lh + 2 * PAD for rows in layouts]
    lines = [max(heights[i:i + across]) for i in range(0, len(chosen), across)]
    W, H = width, sum(lines) + gap * (len(lines) - 1)
    bar_rows = [r for rows in layouts for r in rows if r[0] == 'bar']
    lw = max([len(r[1]) for r in bar_rows] + [0]) + 2   # the label column, the same on every card
    vw = max([len(r[4]) for r in bar_rows] + [0]) + 2   # the value column
    # Keep at least 8 cells for bar tracks even if labels/values are unusually wide
    if bar_rows and lw + vw > cols - 8:
        lw = min(lw, max(8, cols - vw - 8))

    canvas = Image.new('RGB', (W, H), theme['bg'])
    d = ImageDraw.Draw(canvas)
    surface = theme['surface']

    def draw(p):
        """Every card with its bars p (0 to 1) of the way to full."""
        for k, rows in enumerate(layouts):
            x, y = (k % across) * (cardw + gap), sum(lines[:k // across]) + gap * (k // across)
            box = [x + PAD, y + PAD + lh // 2, x + cardw - PAD - 1, y + heights[k] - PAD - lh // 2]
            d.rectangle(box, fill=surface, outline=theme['line'])
            x0 = x + PAD + 2 * cw
            for r, row in enumerate(rows):
                y0 = y + PAD + (r + 1) * lh
                if row[0] == 'title':
                    spaced(d, x0, y0 - (head.size - font.size) // 2, row[1].upper(), head, theme['text'], title_gap)
                    if row[2]:
                        paint.text(d, x0 + (cols - len(row[2])) * cw, y0, row[2], theme['value'])
                elif row[0] == 'text':
                    paint.text(d, x0, y0, row[2][:cols], theme[row[1]])
                elif row[0] == 'section':
                    mid = y0 + lh // 2
                    d.line([(box[0], mid), (box[2], mid)], fill=theme['line'])
                    label = f' {row[1]} '
                    d.rectangle([x0, y0, x0 + len(label) * cw, y0 + lh - 1], fill=surface)
                    paint.text(d, x0, y0, label, theme['muted'])
                else:
                    _, label, v, peak, text, _ = row
                    paint.text(d, x0, y0, label[:max(1, lw - 1)], theme['muted'])
                    bx0, bx1 = x0 + lw * cw, x0 + (cols - vw) * cw
                    b0, b1 = y0 + lh // 3, y0 + lh - lh // 3
                    if bx1 > bx0:
                        d.rectangle([bx0, b0, bx1, b1], fill=theme['track'])
                        end = bx0 + (bx1 - bx0) * v / peak * p
                        if end > bx0:
                            d.rectangle([bx0, b0, end, b1], fill=theme['accent'])
                    paint.text(d, x0 + (cols - len(text)) * cw, y0, text, theme['value'])
        return canvas.quantize(palette=pal, dither=Image.Dither.NONE)

    n = max(2, round(fill * fps)) if gif else 1
    frames = [draw(1 - (1 - k / (n - 1)) ** 3 if n > 1 else 1.0) for k in range(n)]
    durations = [round(1000 / fps)] * (n - 1) + [max(round(1000 / fps), round(hold * 1000))]

    buf = io.BytesIO()
    if gif:
        frames[0].save(buf, format='GIF', save_all=True, append_images=frames[1:], duration=durations,
                       disposal=1, optimize=True)
        with Image.open(io.BytesIO(buf.getvalue())) as im:
            stored = im.n_frames
    else:
        frames[0].save(buf, format='PNG', optimize=True)
        stored = 1

    data = buf.getvalue()
    info = {
        'width': W, 'height': H, 'configs': [c.get('id', '?') for c in chosen],
        'frames': stored, 'bytes': len(data),
        'font': Path(font_name).name if font_name and '/' in font_name else font_name,
        'head_font': Path(head_name).name if head_name and '/' in head_name else (head_name or font_name),
    }
    return data, info


def non_external_recipes():
    out = []
    for f in sorted(ROOT.glob('*/*/*/*/kindling.json')):
        rel = f.parent.relative_to(ROOT).as_posix()
        if rel.split('/')[0] in NOT_RECIPES or rel.startswith('.'):
            continue
        k = json.loads(f.read_text())
        if k.get('status') != 'external':
            out.append(rel)
    return out


def parse_args(argv):
    ap = argparse.ArgumentParser(
        prog='card.py',
        description='Draw docs/card.png from kindling.json (single file, recipe folder(s), or every non-external recipe).',
    )
    ap.add_argument('targets', nargs='*',
                    help='recipe folder(s) or a single kindling.json (omit to process every non-external recipe)')
    ap.add_argument('--config', help='single-file/folder mode: config id (default: default_config, else first)')
    ap.add_argument('--all', action='store_true', help='draw every config in kindling.json, stacked (see --across)')
    ap.add_argument('--across', type=int, default=1, help='with --all: cards side by side in each row')
    ap.add_argument('--out', help='output file path (single target only; default card.png for JSON, <dir>/docs/card.png for dirs)')
    ap.add_argument('--check', action='store_true', help='write nothing; exit 1 when any card is missing or out of date')
    ap.add_argument('--dry-run', action='store_true', help='render in memory to validate, writing nothing')
    ap.add_argument('--width', type=int, default=800, help='image width in pixels')
    ap.add_argument('--light', action='store_true', help='the light theme (default dark)')
    ap.add_argument('--font', help='a monospace TrueType file (default bundled JetBrainsMono-Regular.ttf)')
    ap.add_argument('--display-font', help='the title TrueType file (default bundled SpaceGrotesk-Bold.ttf)')
    ap.add_argument('--font-size', type=int, default=14)
    ap.add_argument('--fps', type=float, default=25.0, help='GIF only')
    ap.add_argument('--fill', type=float, default=1.2, help='GIF only: seconds the bars take to fill')
    ap.add_argument('--hold', type=float, default=4.0, help='GIF only: seconds to show the full card')
    args = ap.parse_args(argv)
    if args.fps <= 0:
        ap.error('--fps must be above 0')
    if args.out and len(args.targets) != 1:
        ap.error('--out can only be used with a single target')
    if args.check and args.dry_run:
        ap.error('--check and --dry-run are mutually exclusive')
    return args


def resolve_targets(args):
    """-> list of (kindling_path, out_path)"""
    if not args.targets:
        return [(ROOT / rel / 'kindling.json', ROOT / rel / 'docs' / 'card.png') for rel in non_external_recipes()]

    pairs = []
    for raw in args.targets:
        p = Path(raw)
        if not p.exists() and (ROOT / raw).exists():
            p = ROOT / raw
        if p.is_file():
            out = Path(args.out) if args.out else Path('card.png')
            pairs.append((p, out))
        elif p.is_dir():
            kj = p / 'kindling.json'
            if not kj.is_file():
                sys.exit(f'card.py: {raw}: no kindling.json')
            out = Path(args.out) if args.out else (p / 'docs' / 'card.png')
            pairs.append((kj, out))
        else:
            sys.exit(f'card.py: {raw}: not found')
    return pairs


def main(argv=None):
    args = parse_args(sys.argv[1:] if argv is None else argv)
    pairs = resolve_targets(args)
    hardware_map = load_hardware()

    stale = []
    written = 0
    for kj, out in pairs:
        gif = out.name.lower().endswith('.gif')
        data, info = render_card_bytes(
            kj,
            config=args.config,
            all_configs=args.all,
            across=args.across,
            width=args.width,
            light=args.light,
            font_path=args.font,
            display_font_path=args.display_font,
            font_size=args.font_size,
            gif=gif,
            fps=args.fps,
            fill=args.fill,
            hold=args.hold,
            hardware_map=hardware_map,
        )
        try:
            display_out = out.resolve().relative_to(ROOT).as_posix()
        except ValueError:
            display_out = str(out)

        existing = out.read_bytes() if out.is_file() else None
        changed = existing != data

        if args.dry_run:
            status = 'would write' if changed else 'current'
            print(f"{display_out}: {info['width']}x{info['height']}, {', '.join(info['configs'])}, "
                  f"{info['bytes'] / 1024:.0f} KiB ({status})")
            continue

        if args.check:
            if changed:
                stale.append(display_out)
                print(f'card: out of date: {display_out}', file=sys.stderr)
            continue

        if changed:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(data)
            written += 1
            tag = 'wrote'
        else:
            tag = 'unchanged'
        print(f"{display_out}: {info['width']}x{info['height']}, {len(info['configs'])} config"
              f"{'s' if len(info['configs']) > 1 else ''} ({', '.join(info['configs'])}), "
              f"{info['frames']} frame{'s' if info['frames'] > 1 else ''}, {info['bytes'] / 1024:.0f} KiB, "
              f"font {info['font']}, title {info['head_font']} ({tag})")

    if args.check:
        if stale:
            print(f'card: {len(stale)} card(s) out of date (run python3 tools/card.py)', file=sys.stderr)
            sys.exit(1)
        print(f'card: {len(pairs)} card(s) up to date')
    elif args.dry_run:
        print(f'card: {len(pairs)} card(s) rendered ok (dry run)')
    else:
        print(f'card: {len(pairs)} card(s) checked, {written} written')


if __name__ == '__main__':
    main()
