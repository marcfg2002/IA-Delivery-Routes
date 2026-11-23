"""Genera capturas de código legibles: marco tipo editor + nombre de archivo + números de línea."""
import sys
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import ImageFormatter

def shot(code, title, out, first_line=1):
    fmt = ImageFormatter(font_name="DejaVu Sans Mono", font_size=20, style="one-dark",
                         line_numbers=True, line_number_start=first_line, line_number_bg="#21252b",
                         line_number_fg="#636d83", line_number_separator=False, image_pad=22, line_pad=6)
    body = Image.open(BytesIO(highlight(code, PythonLexer(), fmt))).convert("RGB")
    bar = 44; m = 0
    img = Image.new("RGB", (body.width, body.height + bar), "#21252b")
    d = ImageDraw.Draw(img)
    for i, c in enumerate(["#ff5f57", "#febc2e", "#28c840"]):
        d.ellipse((18 + i * 24, 15, 32 + i * 24, 29), fill=c)
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 17)
    d.text((100, 12), title, fill="#abb2bf", font=f)
    img.paste(body, (0, bar))
    img.save(out)
    print(out, img.size)

def snippet(path, start_pat, end_pat, dedent=0):
    lines = open(path, encoding="utf-8").read().splitlines()
    s = next(i for i, l in enumerate(lines) if start_pat in l)
    e = next(i for i, l in enumerate(lines) if i >= s and end_pat in l)
    return "\n".join(l[dedent:] for l in lines[s:e + 1]), s + 1

if __name__ == "__main__":
    code, n = snippet("src/ia_delivery/sql_loader.py", "def parse_sql_dump", "return tables")
    shot(code, "src/ia_delivery/sql_loader.py", "docs/img/code/f0_parse_sql_v2.png", n)
    code, n = snippet("src/ia_delivery/data.py", 'lineas = tables["LineasPedido"].merge', 'orders["MargenJITDias"]')
    shot(code, "src/ia_delivery/data.py  ·  build_orders()", "docs/img/code/f1_calculo_caducidad_v2.png", n)
