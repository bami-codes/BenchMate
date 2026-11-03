"""Neutral intended-design schematics for Spark vision input.

Same visual grammar as examples/vision-inputs/2026-10-31/case-01.png, which Spark read
correctly: IEC rectangles, plain value labels, IN / OUT / REF terminals.
No case names, causes, hidden parts, chips or context boxes. Neutral file names.

Run: python3 make_design.py  (needs Python Playwright + Chromium).
Stock revision 2026-11-03: the resistor kit has no 22 kOhm, so R2 in design-02 and design-04
is 20 kOhm. This copy writes only design-02 and design-04 into the folder that holds it;
the 2026-11-02 originals stay unchanged.
"""
import asyncio, json, pathlib
from playwright.async_api import async_playwright

OUT = pathlib.Path(__file__).resolve().parent
W, H = 1200, 650
SW = 4  # stroke width

def svg(body):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<rect width="100%" height="100%" fill="#fff"/>
<g fill="none" stroke="#000" stroke-width="{SW}" stroke-linecap="square">{body}</g></svg>'''

def text(x, y, s, size=26, anchor='start'):
    return f'<text x="{x}" y="{y}" font-family="DejaVu Sans, Arial, sans-serif" font-size="{size}" fill="#000" stroke="none" text-anchor="{anchor}">{s}</text>'

def wire(x1, y1, x2, y2):
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"/>'

def dot(x, y):
    return f'<circle cx="{x}" cy="{y}" r="6" fill="#000" stroke="none"/>'

def res_h(x, y, label, value):
    """Horizontal resistor body from x to x+188 centred on wire y."""
    return (f'<rect x="{x}" y="{y-24}" width="188" height="48" fill="#fff"/>'
            + text(x + 20, y - 58, f'{label}  {value}'))

def res_v(x, y, label, value):
    """Vertical resistor body from y to y+140 centred on wire x."""
    return (f'<rect x="{x-24}" y="{y}" width="48" height="140" fill="#fff"/>'
            + text(x + 42, y + 80, f'{label}  {value}'))

def cap_v(x, y, label, value):
    """Vertical capacitor: plates at y and y+22 centred on wire x; caller draws leads."""
    return (f'<rect x="{x-52}" y="{y+2}" width="104" height="18" fill="#fff" stroke="none"/>'
            + wire(x - 50, y, x + 50, y) + wire(x - 50, y + 22, x + 50, y + 22)
            + text(x + 70, y + 20, f'{label}  {value}'))

TOP, BOT = 230, 520
TITLE = text(46, 56, 'Intended schematic', 26)

def terminals(out_x=900, ref_end=None):
    return (TITLE + text(86, 196, 'IN') + text(out_x - 24, 196, 'OUT') + text(86, BOT + 46, 'REF'))

def design_01():  # R in series, C to REF
    node = 650
    b = [wire(120, TOP, 300, TOP), res_h(300, TOP, 'R1', '4.7 kΩ'), wire(488, TOP, 900, TOP), dot(node, TOP),
         wire(node, TOP, node, 345), cap_v(node, 345, 'C1', '1 µF'), wire(node, 367, node, BOT), wire(120, BOT, node, BOT)]
    return ''.join(b) + terminals()

def design_02():  # R in series; two C and one R from the output node to REF
    xs = [480, 740, 1000]
    b = [wire(120, TOP, 200, TOP), res_h(200, TOP, 'R1', '10 kΩ'), wire(388, TOP, 1120, TOP)]
    for x in xs: b.append(dot(x, TOP))
    b += [wire(xs[0], TOP, xs[0], 345), cap_v(xs[0], 345, 'C1', '1 µF'), wire(xs[0], 367, xs[0], BOT),
          wire(xs[1], TOP, xs[1], 345), cap_v(xs[1], 345, 'C2', '0.1 µF'), wire(xs[1], 367, xs[1], BOT),
          wire(xs[2], TOP, xs[2], 300), res_v(xs[2], 300, 'R2', '20 kΩ'), wire(xs[2], 440, xs[2], BOT),
          wire(120, BOT, xs[2], BOT), dot(xs[0], BOT), dot(xs[1], BOT)]
    return ''.join(b) + terminals(out_x=1120)

def design_03():  # two resistors in series, C to REF
    node = 760
    b = [wire(120, TOP, 190, TOP), res_h(190, TOP, 'R1', '10 kΩ'), wire(378, TOP, 440, TOP),
         res_h(440, TOP, 'R2', '10 kΩ'), wire(628, TOP, 1000, TOP), dot(node, TOP),
         text(409, TOP + 52, 'N1', anchor='middle'),
         wire(node, TOP, node, 345), cap_v(node, 345, 'C1', '1 µF'), wire(node, 367, node, BOT), wire(120, BOT, node, BOT)]
    return ''.join(b) + terminals(out_x=1000)

def design_04():  # resistor divider
    node = 650
    b = [wire(120, TOP, 300, TOP), res_h(300, TOP, 'R1', '4.7 kΩ'), wire(488, TOP, 900, TOP), dot(node, TOP),
         wire(node, TOP, node, 305), res_v(node, 305, 'R2', '20 kΩ'), wire(node, 445, node, BOT), wire(120, BOT, node, BOT)]
    return ''.join(b) + terminals()

def design_05():  # IN wired straight to OUT; R and C in parallel from that node to REF
    xr, xc = 480, 800
    b = [wire(120, TOP, 900, TOP), dot(xr, TOP), dot(xc, TOP),
         wire(xr, TOP, xr, 305), res_v(xr, 305, 'R1', '10 kΩ'), wire(xr, 445, xr, BOT),
         wire(xc, TOP, xc, 345), cap_v(xc, 345, 'C1', '1 µF'), wire(xc, 367, xc, BOT),
         wire(120, BOT, xc, BOT), dot(xr, BOT)]
    return ''.join(b) + terminals()

def design_06():  # NPN switch with an LED load
    x=600; base_y=420
    b=[TITLE,
       text(x+20, 62, '5V'), wire(x, 72, x, 90), res_v(x, 90, 'R2', '1 kΩ'), wire(x, 230, x, 250),
       # LED: anode at top, triangle pointing down, bar at cathode
       f'<polygon points="{x-30},250 {x+30},250 {x},290" fill="#fff"/>', wire(x-30, 290, x+30, 290),
       '<g stroke-width="3">' + wire(x+38, 262, x+62, 238) + wire(x+44, 276, x+68, 252) + '</g>',
       '<polygon points="' + f'{x+62},238 {x+50},242 {x+58},250' + '" fill="#000" stroke="none"/>',
       '<polygon points="' + f'{x+68},252 {x+56},256 {x+64},264' + '" fill="#000" stroke="none"/>',
       text(x+84, 280, 'D1  red LED'),
       wire(x, 290, x, 330), dot(x, 330), text(x-84, 340, 'COL'),
       wire(x, 330, x, 375),
       # NPN transistor
       f'<circle cx="{x-20}" cy="{base_y}" r="52" fill="none"/>',
       wire(x-40, base_y-32, x-40, base_y+32),
       wire(x-40, base_y-14, x, base_y-45), wire(x, base_y-45, x, 375),
       wire(x-40, base_y+14, x, base_y+45),
       '<polygon points="' + f'{x},{base_y+45} {x-16},{base_y+42} {x-8},{base_y+30}' + '" fill="#000" stroke="none"/>',
       text(x+50, base_y+10, 'Q1  BC547B'),
       text(x-96, base_y-10, 'B', 18), text(x+12, base_y-58, 'C', 18), text(x+12, base_y+92, 'E', 18),
       wire(x, base_y+45, x, 560), text(x-26, 600, 'GND'), wire(x-30, 560, x+30, 560),
       # base drive
       wire(120, base_y, 300, base_y), res_h(300, base_y, 'R1', '4.7 kΩ'), wire(488, base_y, x-40, base_y),
       text(86, base_y-34, 'IN')]
    return ''.join(b)

DESIGNS = {'design-02': design_02, 'design-04': design_04}

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={'width': W, 'height': H})
        for name, fn in DESIGNS.items():
            s = svg(fn())
            (OUT / f'{name}.svg').write_text(s, encoding='utf-8')
            await pg.set_content(f'<html><body style="margin:0">{s}</body></html>')
            await pg.screenshot(path=str(OUT / f'{name}.png'), clip={'x': 0, 'y': 0, 'width': W, 'height': H})
        await b.close()

asyncio.run(main())
print('ok')
