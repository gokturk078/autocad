"""
Pafta Çerçevesi ve İslik Kutusu
================================
A1/A2/A3 standart kağıt boyutları, çizim sınırları,
pafta çerçevesi ve profesyonel islik kutusu (title block).

AIA-standard layer sistemi setup'ı da bu modülde.
"""

from __future__ import annotations

from datetime import datetime

import ezdxf
from ezdxf.document import Drawing
from ezdxf.layouts import Modelspace


# ══════════════════════════════════════════════════════════════════════════════
# Kağıt Boyutları (mm → m conversion for modelspace)
# ══════════════════════════════════════════════════════════════════════════════

PAPER_SIZES: dict[str, dict] = {
    "A1": {"width": 841, "height": 594, "margin": 15},
    "A2": {"width": 594, "height": 420, "margin": 15},
    "A3": {"width": 420, "height": 297, "margin": 10},
}

# Title block (islik kutusu) boyutu — pafta sağ alt köşesinde
TITLE_BLOCK_W = 180   # mm
TITLE_BLOCK_H = 60    # mm


# ══════════════════════════════════════════════════════════════════════════════
# AIA Layer Sistemi
# ══════════════════════════════════════════════════════════════════════════════

AIA_LAYERS: dict[str, dict] = {
    # Kat Planı
    "A-WALL":       {"color": 7, "lineweight": 70,  "desc": "Dış duvar"},
    "A-WALL-INT":   {"color": 7, "lineweight": 50,  "desc": "İç duvar"},
    "A-WALL-PRTN":  {"color": 8, "lineweight": 35,  "desc": "Bölme duvar"},
    "A-DOOR":       {"color": 4, "lineweight": 35,  "desc": "Kapılar"},
    "A-GLAZ":       {"color": 5, "lineweight": 35,  "desc": "Pencereler"},
    "A-FURN":       {"color": 3, "lineweight": 18,  "desc": "Mobilya"},
    "A-STRS":       {"color": 6, "lineweight": 35,  "desc": "Merdiven"},
    "A-ELEV":       {"color": 6, "lineweight": 35,  "desc": "Asansör"},
    "A-COLS":       {"color": 1, "lineweight": 50,  "desc": "Kolonlar"},
    "A-FLOR":       {"color": 3, "lineweight": 18,  "desc": "Zemin kaplama"},
    "A-HATCH":      {"color": 2, "lineweight": 9,   "desc": "Hatch dolgu"},
    "A-WALL-HATCH": {"color": 8, "lineweight": 0,   "desc": "Duvar kesit hatch"},
    "A-FLOR-HATCH": {"color": 253, "lineweight": 0, "desc": "Zemin hatch (ıslak)"},
    "A-DIMS":       {"color": 1, "lineweight": 18,  "desc": "Ölçülendirme"},
    "A-TEXT":       {"color": 2, "lineweight": 25,  "desc": "Metin"},
    "A-ANNO":       {"color": 2, "lineweight": 18,  "desc": "Oda/Alan notasyonu"},
    "A-GRID":       {"color": 9, "lineweight": 9,   "desc": "Aks gridleri"},
    "A-BNDRY":      {"color": 7, "lineweight": 70,  "desc": "Yapı sınırı"},
    # Vaziyet Planı
    "A-SITE":       {"color": 3, "lineweight": 50,  "desc": "Vaziyet"},
    "A-SITE-ROAD":  {"color": 8, "lineweight": 35,  "desc": "Yollar"},
    "A-SITE-PARK":  {"color": 4, "lineweight": 25,  "desc": "Otopark"},
    "A-SITE-GREEN": {"color": 3, "lineweight": 18,  "desc": "Yeşil alan"},
    "A-SITE-DIM":   {"color": 1, "lineweight": 18,  "desc": "Vaziyet ölçü"},
    # Çatı
    "A-ROOF":       {"color": 7, "lineweight": 50,  "desc": "Çatı"},
    "A-ROOF-SLOPE": {"color": 8, "lineweight": 18,  "desc": "Çatı eğim"},
    # Kesit
    "A-SECT":       {"color": 7, "lineweight": 70,  "desc": "Kesit duvar"},
    "A-SECT-SLAB":  {"color": 8, "lineweight": 50,  "desc": "Kesit döşeme"},
    "A-SECT-HATCH": {"color": 2, "lineweight": 9,   "desc": "Kesit hatch"},
    "A-SECT-DIM":   {"color": 1, "lineweight": 18,  "desc": "Kesit ölçü"},
    "A-SECT-TEXT":  {"color": 7, "lineweight": 18,  "desc": "Kesit metin"},
    # Görünüş
    "A-ELEV-WALL":  {"color": 7, "lineweight": 50,  "desc": "Görünüş duvar"},
    "A-ELEV-GLAZ":  {"color": 5, "lineweight": 35,  "desc": "Görünüş pencere"},
    "A-ELEV-DOOR":  {"color": 4, "lineweight": 35,  "desc": "Görünüş kapı"},
    "A-ELEV-DIM":   {"color": 1, "lineweight": 18,  "desc": "Görünüş ölçü"},
    "A-ELEV-TEXT":  {"color": 7, "lineweight": 18,  "desc": "Görünüş metin"},
    # Pafta
    "A-FRAME":      {"color": 7, "lineweight": 50,  "desc": "Pafta çerçevesi"},
    "A-TITLE":      {"color": 7, "lineweight": 25,  "desc": "İslik kutusu"},
}


# ══════════════════════════════════════════════════════════════════════════════
# Setup Fonksiyonları
# ══════════════════════════════════════════════════════════════════════════════

def setup_layers(doc: Drawing) -> None:
    """Tüm AIA layer'larını DXF document'a ekle."""
    for name, props in AIA_LAYERS.items():
        if name not in doc.layers:
            doc.layers.add(
                name,
                color=props["color"],
                lineweight=props["lineweight"],
            )


def setup_text_styles(doc: Drawing) -> None:
    """Metin stilleri tanımla — AutoCAD built-in fontlar."""
    styles = doc.styles

    # txt.shx = AutoCAD'in her sürümünde bulunan varsayılan font
    if "TITLE" not in styles:
        styles.new("TITLE", dxfattribs={"font": "txt", "height": 0})
    if "ROOM_NAME" not in styles:
        styles.new("ROOM_NAME", dxfattribs={"font": "txt", "height": 0})
    if "DIM" not in styles:
        styles.new("DIM", dxfattribs={"font": "txt", "height": 0})
    if "ANNO" not in styles:
        styles.new("ANNO", dxfattribs={"font": "txt", "height": 0})


def setup_dim_style(doc: Drawing) -> None:
    """Boyutlandırma stili tanımla."""
    if "ARCH_DIM" not in doc.dimstyles:
        dim = doc.dimstyles.new("ARCH_DIM")
        dim.dxf.dimtxt = 0.10     # metin yüksekliği (m)
        dim.dxf.dimasz = 0.08     # ok boyu (m)
        dim.dxf.dimexe = 0.03     # extension line extension
        dim.dxf.dimexo = 0.05     # extension line offset
        dim.dxf.dimgap = 0.03     # metin gap
        dim.dxf.dimtih = 0        # metin yatay hizalama — inside horizontal off
        dim.dxf.dimtoh = 0        # outside horizontal off
        dim.dxf.dimdec = 2        # ondalık basamak
        dim.dxf.dimclrd = 1       # dim line renk — kırmızı
        dim.dxf.dimclre = 1       # extension line renk


def create_new_dxf() -> Drawing:
    """Yapılandırılmış yeni DXF document oluştur — R2000 (tüm AutoCAD sürümleri)."""
    doc = ezdxf.new("R2000")

    # Header — encoding + metric
    doc.header["$INSUNITS"] = 6      # Metre
    doc.header["$MEASUREMENT"] = 1   # Metrik
    doc.header["$DWGCODEPAGE"] = "ANSI_1254"  # Türkçe Windows-1254

    # Layer'lar
    setup_layers(doc)

    # Metin stilleri
    setup_text_styles(doc)

    # Dim stili
    setup_dim_style(doc)

    return doc


# ══════════════════════════════════════════════════════════════════════════════
# Pafta Çerçevesi
# ══════════════════════════════════════════════════════════════════════════════

def draw_sheet_border(
    msp: Modelspace,
    paper_size: str = "A2",
    scale: float = 100.0,
) -> tuple[float, float, float, float]:
    """
    Pafta çerçevesini çiz.

    Args:
        msp: Modelspace layout
        paper_size: "A1", "A2", "A3"
        scale: Çizim ölçeği (100 = 1/100)

    Returns:
        (x_min, y_min, x_max, y_max) — çizim alanı sınırları (model koordinat)
    """
    ps = PAPER_SIZES.get(paper_size, PAPER_SIZES["A2"])
    margin = ps["margin"]

    # Kağıt boyutunu model koordinatına çevir (mm → m, ölçek uygula)
    pw = ps["width"] / 1000.0 * scale    # m
    ph = ps["height"] / 1000.0 * scale   # m
    mg = margin / 1000.0 * scale         # m

    # Dış çerçeve
    msp.add_lwpolyline(
        [(0, 0), (pw, 0), (pw, ph), (0, ph), (0, 0)],
        dxfattribs={"layer": "A-FRAME", "lineweight": 70},
    )

    # İç çerçeve (çizim alanı)
    x_min = mg
    y_min = mg
    x_max = pw - mg
    y_max = ph - mg

    msp.add_lwpolyline(
        [(x_min, y_min), (x_max, y_min), (x_max, y_max), (x_min, y_max), (x_min, y_min)],
        dxfattribs={"layer": "A-FRAME", "lineweight": 50},
    )

    return (x_min, y_min, x_max, y_max)


# ══════════════════════════════════════════════════════════════════════════════
# İslik Kutusu (Title Block)
# ══════════════════════════════════════════════════════════════════════════════

def draw_title_block(
    msp: Modelspace,
    drawing_area: tuple[float, float, float, float],
    scale: float = 100.0,
    project_name: str = "Mimari Proje",
    sheet_title: str = "Kat Planı",
    sheet_scale: str = "1/100",
    sheet_number: str = "A-01",
    total_sheets: int = 7,
    architect: str = "AutoCA AI Generator",
    city: str = "İstanbul",
    date: str = "",
    revision: str = "00",
) -> None:
    """
    İslik kutusunu çiz — sağ alt köşe.

    ┌───────────────────────────────────┐
    │ PROJE ADI:  [proje_name]          │
    │ MİMAR:      [architect]           │
    │ PAFTA:      [sheet_title]         │
    │ ÖLÇEK:      [sheet_scale]         │
    │ TARİH:      [date]               │
    │ PAFTA NO:   [sheet_number]/[total]│
    │ REVİZYON:   [revision]            │
    │ ŞEHİR:      [city]               │
    └───────────────────────────────────┘
    """
    if not date:
        date = datetime.now().strftime("%d.%m.%Y")

    _, _, x_max, y_min = drawing_area

    # Title block boyutu (model koordinatlarında)
    tb_w = TITLE_BLOCK_W / 1000.0 * scale
    tb_h = TITLE_BLOCK_H / 1000.0 * scale

    # Sol alt köşe
    tx = x_max - tb_w
    ty = y_min

    # Kutu çerçevesi
    msp.add_lwpolyline(
        [(tx, ty), (tx + tb_w, ty), (tx + tb_w, ty + tb_h),
         (tx, ty + tb_h), (tx, ty)],
        dxfattribs={"layer": "A-TITLE"},
    )

    # Satır yüksekliği
    row_h = tb_h / 9  # 8 satır + 1 başlık
    text_h = row_h * 0.45  # metin yüksekliği

    # Başlık satırı (üst — bold)
    header_y = ty + tb_h - row_h
    msp.add_line(
        (tx, header_y), (tx + tb_w, header_y),
        dxfattribs={"layer": "A-TITLE"},
    )

    # Başlık metni
    msp.add_text(
        "AutoCA — AI MİMARİ PROJE",
        dxfattribs={
            "layer": "A-TITLE",
            "height": text_h * 1.2,
            "style": "TITLE",
        },
    ).set_placement((tx + tb_w / 2, header_y + row_h * 0.3), align=ezdxf.enums.TextEntityAlignment.CENTER)

    # Veri satırları
    rows = [
        ("PROJE", project_name),
        ("MİMAR", architect),
        ("PAFTA", sheet_title),
        ("ÖLÇEK", sheet_scale),
        ("TARİH", date),
        ("PAFTA NO", f"{sheet_number}/{total_sheets:02d}"),
        ("REVİZYON", revision),
        ("ŞEHİR", city),
    ]

    label_x = tx + tb_w * 0.03
    value_x = tx + tb_w * 0.35
    divider_x = tx + tb_w * 0.33

    for i, (label, value) in enumerate(rows):
        row_y = header_y - (i + 1) * row_h

        # Yatay ayırıcı
        if i > 0:
            msp.add_line(
                (tx, row_y + row_h), (tx + tb_w, row_y + row_h),
                dxfattribs={"layer": "A-TITLE"},
            )

        # Dikey ayırıcı (label | value)
        msp.add_line(
            (divider_x, row_y), (divider_x, row_y + row_h),
            dxfattribs={"layer": "A-TITLE"},
        )

        # Label
        msp.add_text(
            label,
            dxfattribs={"layer": "A-TITLE", "height": text_h * 0.8},
        ).set_placement((label_x, row_y + row_h * 0.3))

        # Value
        msp.add_text(
            value,
            dxfattribs={"layer": "A-TITLE", "height": text_h},
        ).set_placement((value_x, row_y + row_h * 0.3))
