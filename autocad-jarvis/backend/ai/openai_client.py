"""OpenRouter/Gemini + OpenAI wrapper — generates Turkish architectural analysis."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import TYPE_CHECKING

from openai import AsyncOpenAI

from models.project import AnalysisResult

if TYPE_CHECKING:
    from models.project import ProjectModel


SYSTEM_PROMPT = (
    "Sen bir Türk mimarlık uzmanısın. "
    "Sana bir AutoCAD projesinin parse edilmiş geometrik verisini JSON olarak vereceğim. "
    "Bu veriyi analiz edip Türkçe, profesyonel ve kısa (max 3 cümle) bir özet yaz. "
    "Özette şunlara değin: toplam alan, oda düzeni ve genel değerlendirme. "
    "Sadece özet yaz. Markdown kullanma. JSON üretme."
)

_FALLBACK_SUMMARY = "AI analizi geçici olarak kullanılamıyor. Proje verileri başarıyla parse edildi."


def _ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class OpenAIClient:
    """Async wrapper — supports OpenRouter (Gemini) and OpenAI direct."""

    def __init__(
        self,
        api_key: str,
        model: str = "google/gemini-2.5-pro",
        mini_model: str = "google/gemini-2.5-flash",
        base_url: str | None = None,
    ) -> None:
        if base_url:
            self.client = AsyncOpenAI(
                api_key=api_key,
                base_url=base_url,
                default_headers={
                    "HTTP-Referer": "https://autocad-jarvis.local",
                    "X-Title": "AutoCA AI Architect",
                },
            ) if api_key else None
            self.provider = "openrouter"
        else:
            self.client = AsyncOpenAI(api_key=api_key) if api_key else None
            self.provider = "openai"
        self.model = model
        self.mini_model = mini_model
        self._api_key = api_key

    async def analyze_project(self, project: ProjectModel) -> AnalysisResult:
        """Generate a Turkish summary of the parsed DXF project."""
        if not self._api_key or self.client is None:
            print(f"[{_ts()}] [OPENAI] WARNING: API key yok, fallback kullanılıyor")
            return self._fallback_result(project)

        chosen_model = self.model if project.room_count > 5 else self.mini_model

        project_data = {
            "toplam_alan_m2": project.total_area_m2,
            "oda_sayisi": project.room_count,
            "odalar": [
                {"ad": r.name, "alan": round(r.area_m2, 1)} for r in project.rooms
            ],
            "kapi_sayisi": project.door_count,
            "pencere_sayisi": project.window_count,
            "toplam_duvar_uzunlugu_m": round(project.total_wall_length_m, 1),
        }

        for attempt in range(2):
            try:
                api_params = {
                    "model": chosen_model,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {
                            "role": "user",
                            "content": f"Proje verisi:\n{json.dumps(project_data, ensure_ascii=False)}",
                        },
                    ],
                }

                if self.provider == "openrouter":
                    api_params["max_tokens"] = 300
                    api_params["temperature"] = 0.3
                else:
                    api_params["max_completion_tokens"] = 300

                response = await self.client.chat.completions.create(**api_params)

                result = AnalysisResult(
                    summary_tr=response.choices[0].message.content.strip(),
                    quick_stats=project_data,
                    generated_at=datetime.now(),
                    model_used=chosen_model,
                    tokens_used=response.usage.total_tokens if response.usage else 0,
                )

                print(f"[{_ts()}] [OPENAI] INFO: Analiz tamamlandı: {chosen_model}, {result.tokens_used} token")
                return result

            except Exception as exc:
                print(f"[{_ts()}] [OPENAI] ERROR: Deneme {attempt + 1} başarısız: {exc}")
                if attempt == 0:
                    await asyncio.sleep(5)

        print(f"[{_ts()}] [OPENAI] WARNING: Tüm denemeler başarısız, fallback kullanılıyor")
        return self._fallback_result(project)

    async def health_check(self) -> bool:
        """Quick API connectivity check — works with OpenRouter and OpenAI."""
        if not self._api_key or self.client is None:
            return False
        try:
            if self.provider == "openrouter":
                # OpenRouter: simple test call
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": "test"}],
                    max_tokens=1,
                )
                return bool(response.choices)
            else:
                await self.client.models.retrieve("gpt-5")
                return True
        except Exception as exc:
            print(f"[{_ts()}] [AI] WARNING: Health check başarısız: {exc}")
            return False

    @staticmethod
    def _fallback_result(project: ProjectModel) -> AnalysisResult:
        return AnalysisResult(
            summary_tr=_FALLBACK_SUMMARY,
            quick_stats={
                "toplam_alan_m2": project.total_area_m2,
                "oda_sayisi": project.room_count,
            },
            generated_at=datetime.now(),
            model_used="fallback",
            tokens_used=0,
        )
