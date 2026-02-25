"""
Gelişmiş Türkçe Mimari Proje NLP Ayrıştırıcı
=============================================
Doğal dil komutlarını yapısal ProjectRequest modeline çevirir.
OpenAI gpt-4o JSON mode kullanır.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from ai.openai_client import OpenAIClient


def _ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ══════════════════════════════════════════════════════════════════════════════
# Pydantic Models — NLP Çıktı Şeması
# ══════════════════════════════════════════════════════════════════════════════

class RoomRequest(BaseModel):
    """Tek oda spesifikasyonu."""
    name: str
    room_type: str = "salon"  # salon, yatak_odasi, mutfak, banyo, wc, koridor, hol, balkon, depo
    min_area_m2: float = 0.0
    count: int = 1
    notes: str = ""


class UnitRequest(BaseModel):
    """Bağımsız bölüm (daire) spesifikasyonu."""
    unit_type: str = "2+1"  # 1+0, 1+1, 2+1, 3+1, 4+1 vb.
    count: int = 1
    rooms: list[RoomRequest] = Field(default_factory=list)
    target_area_m2: float = 0.0
    notes: str = ""


class ParcelRequest(BaseModel):
    """Parsel bilgileri."""
    width: float = 0.0       # m
    depth: float = 0.0       # m
    area_m2: float = 0.0     # m² (doğrudan verilirse)
    taks_limit: float = 0.40
    kaks_limit: float = 2.00
    max_floors: int = 5
    max_height: float = 15.50
    front_setback: float = 5.0
    side_setback: float = 3.0
    rear_setback: float = 3.0
    city: str = "İstanbul"


class FloorConfig(BaseModel):
    """Kat konfigürasyonu."""
    basement_count: int = 0     # Bodrum kat sayısı
    ground_floor: bool = True   # Zemin kat var mı
    normal_floors: int = 4      # Normal kat sayısı
    attic: bool = False         # Çatı katı var mı
    floor_height: float = 2.80  # Brüt kat yüksekliği


class ProjectRequest(BaseModel):
    """Tam proje tanımı — NLP çıktısı."""
    project_name: str = "Yeni Proje"
    building_type: Literal["konut", "ofis", "ticaret", "karma"] = "konut"
    parcel: ParcelRequest = Field(default_factory=ParcelRequest)
    floors: FloorConfig = Field(default_factory=FloorConfig)
    units: list[UnitRequest] = Field(default_factory=list)
    style: Literal["modern", "klasik", "minimalist", "geleneksel"] = "modern"
    orientation: Literal["kuzey", "güney", "doğu", "batı", "belirsiz"] = "belirsiz"
    total_area_m2: float = 0.0
    parking_count: int = 0
    elevator: bool = False
    raw_prompt: str = ""


# ── Eski FAZ 2 modelleri (geriye uyumluluk) ──────────────────────────────────

class FloorPlanRequest(BaseModel):
    """FAZ 2 basit model — geriye uyumluluk için korunuyor."""
    type: Literal["floor_plan", "site_plan", "detail"] = "floor_plan"
    area_m2: float
    rooms: list[RoomRequest]
    orientation: Literal["kuzey", "güney", "doğu", "batı", "belirsiz"] = "belirsiz"
    style: Literal["modern", "klasik", "minimalist", "geleneksel"] = "modern"
    floor: int = 1
    regulations: list[str] = Field(default_factory=list)
    raw_prompt: str = ""


# ══════════════════════════════════════════════════════════════════════════════
# NLP System Prompts
# ══════════════════════════════════════════════════════════════════════════════

PROJECT_NLP_PROMPT = """Sen Türkiye'de çalışan uzman bir mimar ve imar mevzuatı bilirkişisisin.
Kullanıcının Türkçe mimari proje talebini analiz et ve SADECE aşağıdaki JSON şemasına uygun yanıt ver.

KURALLAR:
1. SADECE geçerli JSON döndür. Açıklama, markdown, kod bloğu YOK.
2. Belirtilmeyen parsel için İstanbul varsayılanları kullan (TAKS:0.40, KAKS:2.00, 5 kat).
3. Daire tipleri Türkiye standardına göre:
   - "1+0" (stüdyo): 1 oda = 35-45m²
   - "1+1": salon + 1 yatak = 50-65m²
   - "2+1": salon + 2 yatak = 80-100m²
   - "3+1": salon + 3 yatak = 110-140m²
   - "4+1": salon + 4 yatak = 150-190m²
4. Her daire tipi için otomatik odalar ekle:
   - Salon: min 16m², Yatak: min 9m², Mutfak: min 5m², Banyo: min 3.5m²
   - WC: min 1.2m², Koridor: min 4m², Hol: min 3m²
5. Parsel boyutları belirtilmemişse, toplam alan / kat / TAKS'tan hesapla.
6. Asansör: 4+ kat → zorunlu.
7. Otopark: her 100m² inşaat alanı için 1 araçlık.

JSON ŞEMASI:
{
  "project_name": "<proje adı>",
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
      "unit_type": "<1+0|1+1|2+1|3+1|4+1>",
      "count": <her kattaki adet>,
      "rooms": [
        {"name": "<oda adı>", "room_type": "<tip>", "min_area_m2": <m²>, "count": 1, "notes": ""}
      ],
      "target_area_m2": <m²>,
      "notes": ""
    }
  ],
  "style": "<modern|klasik|minimalist|geleneksel>",
  "orientation": "<kuzey|güney|doğu|batı|belirsiz>",
  "total_area_m2": <m²>,
  "parking_count": <sayı>,
  "elevator": <bool>,
  "raw_prompt": "<orijinal metin>"
}"""

# FAZ 2 eski prompt
SIMPLE_NLP_PROMPT = """Sen bir Türk mimarlık uzmanı ve NLP asistanısın.
Kullanıcının Türkçe mimari talebini analiz et ve SADECE aşağıdaki JSON şemasına uygun bir yanıt ver.

KURALLAR:
1. SADECE JSON döndür. Açıklama, markdown, kod bloğu YOK.
2. Alan belirtilmemişse: 1+1=55m², 2+1=85m², 3+1=120m², 4+1=160m²
3. Oda alanları Türk imar yönetmeliğine göre minimum: salon≥16m², yatak odası≥9m², mutfak≥6m², banyo≥3.5m²
4. "3+1" formatı: 3 yatak odası + 1 salon (Türkiye standardı)
5. Belirtilmeyen odalar için makul varsayılanlar kullan (banyo, wc, koridor)

JSON ŞEMASI:
{
  "type": "floor_plan",
  "area_m2": <sayı>,
  "rooms": [
    {"name": "<oda adı>", "room_type": "<tip>", "min_area_m2": <sayı>, "count": <sayı>, "notes": "<not>"}
  ],
  "orientation": "<kuzey|güney|doğu|batı|belirsiz>",
  "style": "<modern|klasik|minimalist|geleneksel>",
  "floor": <sayı>,
  "regulations": [],
  "raw_prompt": "<kullanıcının orijinal metni>"
}"""


# ══════════════════════════════════════════════════════════════════════════════
# NLPParser
# ══════════════════════════════════════════════════════════════════════════════

class NLPParser:
    """Türkçe mimari komutları yapısal modele çevirir."""

    def __init__(self, openai_client: OpenAIClient) -> None:
        self.client = openai_client

    async def parse_project(self, user_text: str) -> ProjectRequest:
        """Tam proje tanımı ayrıştır (FAZ 3A)."""
        print(f"[{_ts()}] [NLP] INFO: Proje komutu ayrıştırılıyor: '{user_text[:80]}...'")

        if self.client.client is None:
            raise RuntimeError("OpenAI istemcisi yapılandırılmamış (API key eksik).")

        api_params = {
            "model": self.client.model,
            "messages": [
                {"role": "system", "content": PROJECT_NLP_PROMPT},
                {"role": "user", "content": f"Proje talebi: {user_text}"},
            ],
            "response_format": {"type": "json_object"},
        }

        if self.client.provider == "openrouter":
            api_params["max_tokens"] = 1500
            api_params["temperature"] = 0.1
        else:
            api_params["max_completion_tokens"] = 1500

        response = await self.client.client.chat.completions.create(**api_params)

        raw = response.choices[0].message.content
        data = json.loads(raw)  # type: ignore[arg-type]
        data["raw_prompt"] = user_text
        result = ProjectRequest(**data)

        print(f"[{_ts()}] [NLP] INFO: Proje ayrıştırma başarılı: "
              f"{result.building_type}, {len(result.units)} daire tipi, "
              f"{result.floors.normal_floors} kat")
        return result

    async def parse(self, user_text: str) -> FloorPlanRequest:
        """Basit kat planı ayrıştır (FAZ 2 geriye uyumluluk)."""
        print(f"[{_ts()}] [NLP] INFO: Komut ayrıştırılıyor: '{user_text[:60]}...'")

        if self.client.client is None:
            raise RuntimeError("OpenAI istemcisi yapılandırılmamış (API key eksik).")

        api_params = {
            "model": self.client.model,
            "messages": [
                {"role": "system", "content": SIMPLE_NLP_PROMPT},
                {"role": "user", "content": f"Türkçe komut: {user_text}"},
            ],
            "response_format": {"type": "json_object"},
        }

        if self.client.provider == "openrouter":
            api_params["max_tokens"] = 800
            api_params["temperature"] = 0.1
        else:
            api_params["max_completion_tokens"] = 800

        response = await self.client.client.chat.completions.create(**api_params)

        raw = response.choices[0].message.content
        data = json.loads(raw)  # type: ignore[arg-type]
        data["raw_prompt"] = user_text
        result = FloorPlanRequest(**data)
        print(f"[{_ts()}] [NLP] INFO: Ayrıştırma başarılı: {result.area_m2}m², {len(result.rooms)} oda tipi")
        return result
