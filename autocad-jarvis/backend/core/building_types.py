"""
Bina Tipi Şablonları (Building Type Templates)
===============================================
Her bina tipi için mimari kurallar ve standart değerler.
AI Architect bu bilgileri prompt'a enjekte eder.
"""

from __future__ import annotations

# ══════════════════════════════════════════════════════════════════════════════
# Bina Tipi Şablonları
# ══════════════════════════════════════════════════════════════════════════════

BUILDING_TEMPLATES: dict[str, dict] = {
    # ── Konut Apartman ────────────────────────────────────────────────────
    "konut": {
        "display_name": "Konut Apartman",
        "corridor_type": "single-loaded",       # Tek taraflı koridor (tipik apartman)
        "unit_pattern": "mirrored",              # Simetrik daire yerleşimi
        "floor_strategy": "typical",             # Her kat aynı plan
        "common_areas": ["merdiven_holu", "asansor"],
        "typical_rooms": {
            "2+1": [
                {"name": "Salon", "type": "salon", "min_area": 22, "facade": True},
                {"name": "Yatak Odası", "type": "yatak_odasi", "min_area": 14, "facade": True},
                {"name": "Mutfak", "type": "mutfak", "min_area": 8, "facade": False},
                {"name": "Banyo", "type": "banyo", "min_area": 4, "facade": False},
                {"name": "WC", "type": "wc", "min_area": 1.5, "facade": False},
                {"name": "Hol", "type": "hol", "min_area": 5, "facade": False},
            ],
            "3+1": [
                {"name": "Salon", "type": "salon", "min_area": 25, "facade": True},
                {"name": "Ebeveyn Yatak", "type": "yatak_odasi", "min_area": 16, "facade": True},
                {"name": "Çocuk Odası 1", "type": "yatak_odasi", "min_area": 12, "facade": True},
                {"name": "Çocuk Odası 2", "type": "yatak_odasi", "min_area": 12, "facade": True},
                {"name": "Mutfak", "type": "mutfak", "min_area": 10, "facade": False},
                {"name": "Banyo", "type": "banyo", "min_area": 5, "facade": False},
                {"name": "WC", "type": "wc", "min_area": 2, "facade": False},
                {"name": "Hol", "type": "hol", "min_area": 6, "facade": False},
            ],
        },
        "rules": [
            "Salon mutfağa bitişik olmalı (açık plan tercih)",
            "Yatak odaları güneş alan cepheye yerleştirilmeli",
            "WC ve banyo tesisat şaftına yakın olmalı",
            "Hol giriş kapısından tüm odalara erişim sağlamalı",
        ],
    },

    # ── Otel ─────────────────────────────────────────────────────────────
    "otel": {
        "display_name": "Otel",
        "corridor_type": "double-loaded",        # Çift taraflı koridor (otel standart)
        "unit_pattern": "repeating",             # Tekrar eden oda dizilimi
        "floor_strategy": "identical",           # Normal katlar aynı
        "common_areas": ["lobi", "resepsiyon", "restoran", "bar", "toplanti"],
        "typical_rooms": {
            "standart": [
                {"name": "Otel Odası", "type": "yatak_odasi", "min_area": 24, "facade": True},
                {"name": "Banyo", "type": "banyo", "min_area": 5, "facade": False},
            ],
            "suit": [
                {"name": "Salon", "type": "salon", "min_area": 18, "facade": True},
                {"name": "Yatak", "type": "yatak_odasi", "min_area": 20, "facade": True},
                {"name": "Banyo", "type": "banyo", "min_area": 7, "facade": False},
                {"name": "Giyinme", "type": "giyinme", "min_area": 4, "facade": False},
            ],
        },
        "special_floors": {
            "ground": ["lobi", "resepsiyon", "restoran", "bar", "mutfak", "wc_grubu"],
            "top": ["teras", "fitness", "spa", "havuz"],
        },
        "rules": [
            "Koridor genişliği min 1.80m (otel standardı)",
            "Her odanın banyosu içeride olmalı",
            "Yangın merdiveni her 30m'de bir",
            "Oda girişleri koridora açılmalı",
            "Lobi zemin katta, çift yükseklik (6m)",
        ],
    },

    # ── Villa ────────────────────────────────────────────────────────────
    "villa": {
        "display_name": "Villa",
        "corridor_type": "none",                 # Koridor yok, açık plan
        "unit_pattern": "single_unit",           # Tek daire
        "floor_strategy": "differentiated",      # Her kat farklı
        "common_areas": ["garaj", "bahce"],
        "typical_rooms": {
            "zemin": [
                {"name": "Salon", "type": "salon", "min_area": 35, "facade": True},
                {"name": "Mutfak", "type": "mutfak", "min_area": 15, "facade": True},
                {"name": "Yemek Odası", "type": "salon", "min_area": 15, "facade": True},
                {"name": "WC", "type": "wc", "min_area": 3, "facade": False},
                {"name": "Hol", "type": "hol", "min_area": 10, "facade": False},
            ],
            "normal": [
                {"name": "Ebeveyn Yatak", "type": "yatak_odasi", "min_area": 20, "facade": True},
                {"name": "Ebeveyn Banyo", "type": "banyo", "min_area": 8, "facade": False},
                {"name": "Çocuk Odası 1", "type": "yatak_odasi", "min_area": 14, "facade": True},
                {"name": "Çocuk Odası 2", "type": "yatak_odasi", "min_area": 14, "facade": True},
                {"name": "Banyo", "type": "banyo", "min_area": 6, "facade": False},
                {"name": "Koridor", "type": "koridor", "min_area": 8, "facade": False},
            ],
        },
        "rules": [
            "Geniş pencereler ve bahçe bağlantısı",
            "Açık plan tercih (salon-mutfak-yemek)",
            "Ebeveyn yatak en iyi manzaraya bakmalı",
            "Zemin katta misafir WC zorunlu",
        ],
    },

    # ── Ofis ─────────────────────────────────────────────────────────────
    "ofis": {
        "display_name": "Ofis",
        "corridor_type": "open_plan",            # Açık ofis planı
        "unit_pattern": "flexible",              # Esnek bölünme
        "floor_strategy": "typical",
        "common_areas": ["lobi", "toplanti", "wc_grubu", "mutfak"],
        "typical_rooms": {
            "standart": [
                {"name": "Açık Ofis", "type": "salon", "min_area": 60, "facade": True},
                {"name": "Toplantı Odası", "type": "salon", "min_area": 20, "facade": True},
                {"name": "Müdür Odası", "type": "yatak_odasi", "min_area": 16, "facade": True},
                {"name": "WC Grubu", "type": "wc", "min_area": 10, "facade": False},
                {"name": "Mutfak/Pantry", "type": "mutfak", "min_area": 8, "facade": False},
            ],
        },
        "rules": [
            "Açık ofis alanı en az %60",
            "Doğal ışık her çalışma noktasına ulaşmalı",
            "WC grubu her katta zorunlu",
            "Yangın çıkışı her 25m'de",
        ],
    },
}


def get_template(building_type: str) -> dict:
    """Bina tipine göre şablon döndür."""
    # Normalize
    bt = building_type.lower().replace(" ", "_")
    
    # Eşleştirme
    if any(k in bt for k in ("otel", "hotel")):
        return BUILDING_TEMPLATES["otel"]
    elif any(k in bt for k in ("villa", "müstakil")):
        return BUILDING_TEMPLATES["villa"]
    elif any(k in bt for k in ("ofis", "office", "ticari")):
        return BUILDING_TEMPLATES["ofis"]
    else:
        return BUILDING_TEMPLATES["konut"]


def get_template_prompt(building_type: str) -> str:
    """AI prompt'una eklenecek bina tipi bilgisi."""
    t = get_template(building_type)
    
    lines = [
        f"\n═══ BİNA TİPİ ŞABLONu: {t['display_name']} ═══",
        f"Koridor tipi: {t['corridor_type']}",
        f"Daire dizilimi: {t['unit_pattern']}",
        f"Kat stratejisi: {t['floor_strategy']}",
        "",
        "KURALLAR:",
    ]
    for rule in t.get("rules", []):
        lines.append(f"  - {rule}")
    
    if "special_floors" in t:
        lines.append("")
        lines.append("ÖZEL KATLAR:")
        for floor_type, areas in t["special_floors"].items():
            lines.append(f"  {floor_type}: {', '.join(areas)}")
    
    return "\n".join(lines)
