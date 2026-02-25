"""
AI Architect — Gemini 2.5 Pro Powered Mimari Akıl Katmanı (Sprint 7)
=============================================================
Ultra-profesyonel mimari tasarım motoru.

Pipeline:
  1. Kullanıcı prompt → Gemini 2.5 Pro (OpenRouter) (Structured JSON)
  2. Gemini: adjacency graph, constraint-based sizing, sun orientation
  3. Sonuç → ProjectRequest → ProjectBuilder → DXF

Model Stratejisi:
  - Primary: Gemini 2.5 Pro (OpenRouter) — 152 t/s, 1.2s latency
  - Fallback: GPT-5 (OpenAI direct) — 60 t/s, 11s latency
  - OpenAI SDK uyumlu — sadece base_url değişiyor
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime

from dotenv import load_dotenv
from openai import AsyncOpenAI

from ai.nlp_parser import ProjectRequest

# Load .env for standalone usage
load_dotenv()


def _ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _repair_json(raw: str) -> dict:
    """
    Gemini bazen geçersiz JSON üretir (trailing comma, yorum, truncation).
    Bu fonksiyon onarır ve parse eder.
    """
    text = raw.strip()

    # 1. Markdown code fence kaldır (```json ... ```)
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    # 2. // ve /* */ yorum kaldır
    text = re.sub(r"//[^\n]*", "", text)
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)

    # 3. Trailing comma kaldır: ,\s*} veya ,\s*]
    text = re.sub(r",\s*([}\]])", r"\1", text)

    # 4. İlk deneme
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 5. Truncated JSON — auto-close açık parantezleri kapat
    # Gemini bazen max_tokens nedeniyle JSON'u yarıda keser
    in_string = False
    escape = False
    stack = []
    last_good = 0
    for i, ch in enumerate(text):
        if escape:
            escape = False
            continue
        if ch == '\\':
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch in '{[':
            stack.append('}' if ch == '{' else ']')
            last_good = i
        elif ch in '}]':
            if stack:
                stack.pop()
            last_good = i

    if stack:
        # Kesilmiş string'i kapat + açık bracket'ları kapat
        # Son satırdaki açık key/value'yu temizle
        truncated = text.rstrip()
        # Yarım kalmış string/value kapat
        if truncated[-1] not in '}],':
            # Son ',' veya '{' veya '[' a bul
            cut = max(truncated.rfind(','), truncated.rfind('{'), truncated.rfind('['))
            if cut > 0:
                truncated = truncated[:cut+1]
        # Trailing comma temizle
        truncated = re.sub(r",\s*$", "", truncated)
        # Kapanmamış bracket'ları kapat
        closing = ''.join(reversed(stack))
        repaired = truncated + closing
        repaired = re.sub(r",\s*([}\]])", r"\1", repaired)
        try:
            return json.loads(repaired)
        except json.JSONDecodeError:
            pass

    # 6. JSON bloğunu regex ile çıkar
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        extracted = match.group(0)
        extracted = re.sub(r",\s*([}\]])", r"\1", extracted)
        try:
            return json.loads(extracted)
        except json.JSONDecodeError:
            pass

    # 7. Son çare
    return json.loads(raw)


# ══════════════════════════════════════════════════════════════════════════════
# Sprint 7 — Ultra Professional Architect System Prompt
# ══════════════════════════════════════════════════════════════════════════════

ARCHITECT_SYSTEM_PROMPT = """Sen Türkiye'nin en deneyimli A sınıfı mimarlık firmasının baş mimarısın.
30 yıllık meslek deneyimine, 500+ tamamlanmış projeye sahipsin.
Planlı Alanlar Tip İmar Yönetmeliği (Ocak 2026), Binaların Yangından Korunması Hakkında Yönetmelik,
TSE standartları ve Deprem Yönetmeliği'ni ezbere bilirsin.
Belediye ruhsat süreçlerini, yapı denetim gereksinimlerini ve mevzuat değişikliklerini takip edersin.

GÖREV: Kullanıcının mimari proje talebini profesyonel mimar perspektifinden analiz et.
Mevzuata tam uyumlu, ergonomik, sürdürülebilir bir ProjectRequest JSON'u üret.

═══ 1. İMAR MEVZUATI ═══

TAKS (Taban Alanı Kat Sayısı):
  - Ayrık/blok nizam: max 0.40 (imar planı yoksa)
  - TAKS = bina oturum alanı / parsel alanı
  - Emsal harici: yangın merdiveni, sığınak, otopark, tesisat odası

KAKS (Kat Alanı Kat Sayısı):
  - Plan yoksa KAKS verilip TAKS verilmezse → TAKS ≤ 0.60
  - Emsal harici alanlar toplamı ≤ net alan × %30
  - Bodrum otopark emsal harici (ZORUNLU kaydırmak)
  - Deprem yalıtım katı emsal harici (2026 değişiklik)

Çekme Mesafeleri:
  - Ön bahçe: 5.00m (min)
  - Yan bahçe: 3.00m (min, yapı yüksekliğinin H/2 ile hesapla)
  - Arka bahçe: H/2 (min 3.00m)
  - footprint = (parsel_W - 2×yan) × (parsel_D - ön - arka)

Kat Yüksekliği:
  - Konut: brüt 2.80m (net 2.50m), döşeme kalınlığı 0.15m
  - Ticaret/zemin kat: brüt 3.50m (net 3.00m)
  - Bodrum: brüt 2.60m
  - Çatı arası: max 1.80m mesafe

Bina Yüksekliği:
  - Normal yapı: ≤21.50m (±0.00 kotundan saçak/parapet üstüne)
  - Yüksek yapı: >21.50m (özel şartlar + yangın merdiveni zorunlu)
  - 7+ kat → kapalı çıkma yasak

Asansör: ≥4 kat → zorunlu (alan: ~4.0m², kabin 1.10×1.40m)
Yangın Merdiveni: >21.50m → zorunlu (min genişlik 1.20m)
Otopark: Konut: 1 araç/daire, Ofis: 1 araç/30m², Ticaret: 1 araç/20m²

═══ 2. MİNİMUM ODA BOYUTLARI (TSE 12464 + Yönetmelik) ═══

  Oda Tipi          | Min Alan | Min Kenar | Lüks Hedef
  ─────────────────────────────────────────────────────
  Salon/Oturma      |  20 m²   |  3.50m    |  ≥28 m²
  Ebeveyn Yatak     |  14 m²   |  3.00m    |  ≥18 m²
  Çocuk Yatak       |   9 m²   |  2.50m    |  ≥12 m²
  Misafir Yatak     |  10 m²   |  2.80m    |  ≥14 m²
  Mutfak (bağımsız) |   8 m²   |  2.00m    |  ≥12 m²
  Mutfak (açık)     |   6 m²   |  2.00m    |  ≥10 m²
  Banyo             |   4 m²   |  1.80m    |  ≥6 m²
  Ebeveyn Banyo     |   5 m²   |  2.00m    |  ≥7 m²
  WC                |   1.5m²  |  0.90m    |  ≥2.5m²
  Hol/Giriş         |   4 m²   |  1.50m    |  ≥6 m²
  Koridor genişlik  |  1.20m   |   —       |  ≥1.40m
  Balkon derinlik   |  1.20m   |   —       |  ≥2.00m
  Giyinme           |   4 m²   |  1.50m    |  ≥5 m²

→ Her oda ASPECT RATIO: 1:1 ~ 1:2.5 arası (uzun ince oda YASAK)
→ Oda alanı toplamı = target_area × 0.82 (duvar payı %18)

═══ 3. ADJACENCY (YAKINLIK) MATRİSİ ═══

Oda yerleşiminde aşağıdaki kuralları ZORUNLU uygula:

  Salon ↔ Mutfak      : BİTİŞİK (kapı veya açık plan)
  Salon ↔ Balkon       : BİTİŞİK (balkon kapısı salondan)
  Ebeveyn Yatak → Banyo: BİTİŞİK (en-suite)
  Hol → Giriş kapısı   : DOĞRUDAN (ilk giren alan)
  Hol → Salon          : ERİŞİM (en fazla 1 kapı)
  Hol → Koridor        : ERİŞİM
  Çocuk odaları → WC   : YAKIN (koridor üzerinde)
  Mutfak ↕ Banyo/WC    : DÜŞEY HİZA (tesisat şaftı)
  Mutfak → Hol         : 2. çıkış (yangın güvenliği)

═══ 4. GÜNEŞ YÖNÜ OPTİMİZASYONU ═══

  Güney cephe  → Salon, Oturma, Ana balkon (max kış güneşi)
  Güneybatı    → Ebeveyn yatak (akşam güneşi, gün batımı)  
  Doğu cephe   → Mutfak, Çocuk yatak (sabah güneşi)
  Kuzey cephe  → Islak hacimler, koridor, merdiven holü
  Batı cephe   → 2. balkon, misafir odası

═══ 5. KAPI VE PENCERE ÖZELLİKLERİ ═══

Kapı Tipleri:
  - Dış giriş kapısı: 90×210cm, çelik, KOD: K-GR
  - İç oda kapıları: 80×210cm, ahşap, KOD: K-01, K-02...
  - Banyo kapısı: 70×210cm, PVC/ahşap, KOD: K-BN
  - Mutfak kapısı: 80×210cm, ahşap, KOD: K-MT
  - Sürgülü kapı (balkon): 150-200cm genişlik, KOD: K-SG

Pencere Tipleri:
  - Salon pencere: 150×150cm (çift kanat PVC), KOD: P-01
  - Yatak pencere: 120×120cm (tek/çift kanat), KOD: P-02  
  - Mutfak pencere: 100×120cm (tek kanat), KOD: P-03
  - Banyo pencere: 60×60cm (vasistas), KOD: P-04
  - Balkon kapı-pencere: 180×220cm, KOD: P-BK

═══ 6. ÇIKTI KURALLARI ═══

*** KRİTİK HARD RULES — İHLAL EDİLEMEZ ***

HR-1 YÜKSEKLIK: total_height = (basement_count × 2.60) + (ground_floor ? 3.50 : 0) + (normal_floors × floor_height)
     → total_height ≤ max_height ZORUNLU. Aşarsa normal_floors'u AZALT.
     → Varsayılan max_height = 21.50m (belirtilmezse)

HR-2 TAKS: TAKS = footprint / parcel_area → 0.25 ≤ TAKS ≤ taks_limit (max 0.40)
     → footprint = building_width × building_depth
     → building_width = parcel_width - 2×side_setback
     → building_depth = parcel_depth - front_setback - rear_setback
     → TAKS < 0.20 dururu YASAK — arsayı boşa harcıyorsun!

HR-3 KAT SAYISI: normal_floors = min(kullanıcı talebi, max_floors, floor(max_height / floor_height))

HR-4 ODA ALANI: Her odanın width ve depth değerlerini VER. 
     width × depth = min_area_m2. Aspect ratio 1:1 ile 1:2.5 arası.

HR-5 BİNA BOYUTU: parcel bilgisi varsa bina boyutunu HESAPLA:
     building_width = parcel.width - 2 × side_setback
     building_depth = parcel.depth - front_setback - rear_setback
     Bu değerleri JSON'a dahil ET.

1. SADECE geçerli JSON döndür. Açıklama, markdown, kod bloğu YOK.
2. Her oda için gerçekçi alan VE boyut hesapla:
   - width ve depth belirt (aspect ratio 1:1 ~ 1:2.5)
   - Toplamı target_area_m2 × 0.82 ile uyumlu
3. Her oda için face yönü belirt (south/north/east/west/interior)
4. Belirtilmeyen şehir → İstanbul varsayılanları
5. Parsel boyutu yoksa → toplam alan + kat sayısından hesapla
6. room_type: salon, yatak_odasi, mutfak, banyo, wc, hol, koridor, balkon, giyinme
7. Her odada notes: cephe yönü + adjacency bilgisi
8. door_schedule ve window_schedule üret

JSON ŞEMASI:
{
  "project_name": "<proje adı, lokasyon + tip bazlı>",
  "building_type": "<konut|ofis|ticaret|karma>",
  "parcel": {
    "width": <m>, "depth": <m>, "area_m2": <m²>,
    "taks_limit": <0-1>, "kaks_limit": <0-5>,
    "max_floors": <sayı>, "max_height": <m>,
    "front_setback": <m>, "side_setback": <m>, "rear_setback": <m>,
    "city": "<şehir>"
  },
  "floors": {
    "basement_count": <0-3>, "ground_floor": true,
    "normal_floors": <sayı>, "attic": <bool>,
    "floor_height": <m>
  },
  "units": [
    {
      "unit_type": "<1+0|1+1|2+1|3+1|4+1|5+1>",
      "count": <her kattaki adet>,
      "rooms": [
        {
          "name": "<oda Türkçe adı>",
          "room_type": "<tip>",
          "min_area_m2": <m²>,
          "count": 1,
          "notes": "<cephe yönü + adjacency bilgisi>"
        }
      ],
      "target_area_m2": <m²>,
      "notes": ""
    }
  ],
  "style": "<modern|klasik|minimalist|geleneksel>",
  "orientation": "<kuzey|güney|doğu|batı|belirsiz>",
  "total_area_m2": <toplam inşaat alanı>,
  "parking_count": <hesaplanmış otopark sayısı>,
  "elevator": <bool>,
  "door_schedule": [
    {"code": "K-GR", "type": "Dış Giriş", "size": "90x210", "material": "Çelik", "count": 1},
    {"code": "K-01", "type": "İç Kapı", "size": "80x210", "material": "Ahşap", "count": <n>}
  ],
  "window_schedule": [
    {"code": "P-01", "type": "Salon Pencere", "size": "150x150", "material": "PVC Çift Cam", "count": <n>},
    {"code": "P-02", "type": "Yatak Pencere", "size": "120x120", "material": "PVC Çift Cam", "count": <n>}
  ],
  "facade_notes": "<cephe malzemesi, renk, süsleme notları>"
}"""


# ══════════════════════════════════════════════════════════════════════════════
# AIArchitect Class (Sprint 7 — GPT-5)
# ══════════════════════════════════════════════════════════════════════════════

class AIArchitect:
    """
    Gemini 2.5 Pro powered mimari akıl katmanı.
    OpenRouter API üzerinden 10× hızlı structured JSON çıktı.
    
    Fallback: OpenAI GPT-5 (OpenRouter yoksa)
    """

    def __init__(self) -> None:
        # Primary: OpenRouter (Gemini 2.5 Pro)
        or_key = os.getenv("OPENROUTER_API_KEY", "")
        base_url = os.getenv("AI_BASE_URL", "https://openrouter.ai/api/v1")
        self.model = os.getenv("AI_MODEL", "google/gemini-2.5-pro")
        self.fast_model = os.getenv("AI_FAST_MODEL", "google/gemini-2.5-flash")
        self.provider = "openrouter"

        if or_key:
            self.client = AsyncOpenAI(
                api_key=or_key,
                base_url=base_url,
                default_headers={
                    "HTTP-Referer": "https://autocad-jarvis.local",
                    "X-Title": "AutoCA AI Architect",
                },
            )
            self._ready = True
        else:
            # Fallback: OpenAI direct (GPT-5)
            oai_key = os.getenv("OPENAI_API_KEY", "")
            self.client = AsyncOpenAI(api_key=oai_key) if oai_key else None
            self.model = os.getenv("OPENAI_MODEL", "gpt-5")
            self.provider = "openai"
            self._ready = bool(oai_key)

    @property
    def is_ready(self) -> bool:
        return self._ready and self.client is not None

    async def design_project(self, user_prompt: str) -> ProjectRequest:
        """
        Kullanıcı prompt'unu analiz et → professyonel ProjectRequest döndür.
        
        İki aşamalı pipeline:
          1. GPT-5 Thinking mode → spatial layout + compliance pre-check
          2. Structured JSON output → door/window schedule dahil
        """
        if not self.is_ready:
            raise RuntimeError("OpenAI API key yapılandırılmamış (.env dosyasını kontrol edin)")

        print(f"[{_ts()}] [AI-ARCHITECT] 🏗️ Proje tasarlanıyor: '{user_prompt[:80]}...'")
        print(f"[{_ts()}] [AI-ARCHITECT] Model: {self.model} ({self.provider})")

        try:
            # Provider-aware API params
            api_params = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": ARCHITECT_SYSTEM_PROMPT},
                    {"role": "user", "content": f"Proje talebi: {user_prompt}"},
                ],
                "response_format": {"type": "json_object"},
            }

            if self.provider == "openrouter":
                # Gemini: standard params (temperature + max_tokens destekli)
                api_params["max_tokens"] = 8192
                api_params["temperature"] = 0.12
            else:
                # GPT-5: max_completion_tokens + no temperature
                api_params["max_completion_tokens"] = 4000

            response = await self.client.chat.completions.create(**api_params)

            raw = response.choices[0].message.content
            tokens = response.usage.total_tokens if response.usage else 0
            
            print(f"[{_ts()}] [AI-ARCHITECT] ✓ {self.provider.upper()} yanıt aldı ({tokens} token)")

            # Parse JSON (with repair for Gemini quirks)
            data = _repair_json(raw)
            data["raw_prompt"] = user_prompt

            # Strip extra fields GPT might add (door/window schedule etc.)
            # These are logged but not part of ProjectRequest pydantic model
            door_schedule = data.pop("door_schedule", [])
            window_schedule = data.pop("window_schedule", [])
            facade_notes = data.pop("facade_notes", "")

            if door_schedule:
                print(f"[{_ts()}] [AI-ARCHITECT] 📋 Kapı cetveli: {len(door_schedule)} tip")
                for d in door_schedule:
                    print(f"[{_ts()}] [AI-ARCHITECT]   {d.get('code','?')}: "
                          f"{d.get('type','')} {d.get('size','')} "
                          f"{d.get('material','')} ×{d.get('count',0)}")

            if window_schedule:
                print(f"[{_ts()}] [AI-ARCHITECT] 🪟 Pencere cetveli: {len(window_schedule)} tip")
                for w in window_schedule:
                    print(f"[{_ts()}] [AI-ARCHITECT]   {w.get('code','?')}: "
                          f"{w.get('type','')} {w.get('size','')} "
                          f"{w.get('material','')} ×{w.get('count',0)}")

            if facade_notes:
                print(f"[{_ts()}] [AI-ARCHITECT] 🏛️ Cephe: {facade_notes[:100]}")

            # Validate + construct ProjectRequest
            result = ProjectRequest(**data)

            print(f"[{_ts()}] [AI-ARCHITECT] ✓ Proje tasarlandı: "
                  f"{result.building_type}, {len(result.units)} daire tipi, "
                  f"{result.floors.normal_floors} kat, "
                  f"toplam {result.total_area_m2:.0f}m²")

            # Log room details with adjacency
            for unit in result.units:
                room_summary = ", ".join(
                    f"{r.name}({r.min_area_m2}m²)" for r in unit.rooms
                )
                print(f"[{_ts()}] [AI-ARCHITECT]   {unit.unit_type} × {unit.count}: "
                      f"{room_summary}")

            return result

        except json.JSONDecodeError as e:
            print(f"[{_ts()}] [AI-ARCHITECT] ❌ JSON parse hatası: {e}")
            print(f"[{_ts()}] [AI-ARCHITECT] Raw response: {raw[:500] if 'raw' in dir() else 'N/A'}")
            raise RuntimeError(f"{self.provider} geçersiz JSON döndürdü: {e}") from e
        except Exception as e:
            print(f"[{_ts()}] [AI-ARCHITECT] ❌ Hata: {e}")
            raise

    async def health_check(self) -> dict:
        """API bağlantı kontrolü."""
        if not self.is_ready:
            return {"status": "error", "message": "API key eksik"}
        try:
            await self.client.models.retrieve(self.model)
            return {"status": "ok", "model": self.model}
        except Exception as e:
            return {"status": "error", "message": str(e)}
