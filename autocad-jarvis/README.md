# AutoCAD JARVIS AI Copilot

Mimarlar için sıfır-sürtünmeli AI Copilot. AutoCAD'de her Ctrl+S yapışınızda,
DXF dosyanız otomatik parse edilir, AI ile analiz edilir ve sonuçlar gerçek zamanlı
olarak floating panel'de görüntülenir.

## ✨ Özellikler (FAZ 1)

- **Gerçek zamanlı DXF izleme** — watchdog ile dosya değişikliklerini anında yakalar
- **Otomatik DXF parse** — ezdxf ile oda alanları, duvar uzunlukları, kapı/pencere sayımı
- **AI analizi** — OpenAI gpt-4o ile Türkçe mimari özet
- **WebSocket push** — < 2 saniyede panel güncellenir
- **Glassmorphism UI** — Premium, karanlık tema floating panel
- **Auto-reconnect** — Bağlantı kopunca otomatik yeniden bağlanma

## 🚀 Hızlı Başlangıç

### Gereksinimler
- Python 3.11+
- Node.js 18+
- OpenAI API key

### Kurulum

```bash
# 1. Repo klonla
git clone <repo> && cd autocad-jarvis

# 2. Python ortamı
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. Ortam değişkenleri
cp ../.env.example .env
# .env dosyasını aç, OPENAI_API_KEY değerini gir

# 4. Backend başlat
python main.py
# → http://localhost:8765 adresinde çalışır
# → http://localhost:8765/docs adresinde Swagger UI

# 5. Frontend (yeni terminal)
cd ../frontend
npm install
npm run dev
# → http://localhost:3000 adresinde çalışır
```

## 🧪 Test

```bash
# Backend sağlık kontrolü
curl http://localhost:8765/health

# Test DXF üret ve analiz et
curl -X POST http://localhost:8765/project/test

# Klasör izlemeye ekle
curl -X POST http://localhost:8765/watch \
  -H "Content-Type: application/json" \
  -d '{"path": "/Users/username/Desktop"}'
```

## 📋 Kullanım

1. Tarayıcıda `http://localhost:3000` aç
2. Paneli ekranın sağına konumlandır (otomatik sabitlenir)
3. AutoCAD'de `.dxf` dosyası aç
4. **Ctrl+S** yap → panel otomatik güncellenir

## 🏗️ Proje Yapısı

```
autocad-jarvis/
├── backend/
│   ├── main.py               ← FastAPI app + REST endpoints
│   ├── config.py              ← Pydantic BaseSettings
│   ├── core/
│   │   ├── connection_manager.py  ← WebSocket hub
│   │   ├── dxf_parser.py         ← ezdxf → ProjectModel
│   │   └── watcher.py            ← watchdog file watcher
│   ├── ai/
│   │   └── openai_client.py      ← OpenAI gpt-4o wrapper
│   ├── models/
│   │   ├── project.py            ← Pydantic data models
│   │   └── websocket_message.py  ← WS message schema
│   └── routers/
│       └── websocket.py          ← /ws endpoint
│
└── frontend/
    ├── app/
    │   ├── layout.tsx         ← Dark mode root layout
    │   ├── page.tsx           ← Ana JARVIS panel
    │   └── globals.css        ← Glassmorphism CSS
    ├── components/
    │   ├── StatusBar.tsx      ← Bağlantı durumu
    │   ├── ProjectSummary.tsx ← Alan, oda, istatistikler
    │   ├── AIInsightCard.tsx  ← AI analiz kartı
    │   └── ConnectionDot.tsx  ← Durum göstergesi
    ├── hooks/
    │   ├── useWebSocket.ts    ← Auto-reconnect WS hook
    │   └── useProjectState.ts ← Global state (Context)
    └── lib/
        ├── types.ts           ← TypeScript interfaces
        └── constants.ts       ← Sabitler
```

## ⚙️ Ortam Değişkenleri

| Değişken | Açıklama | Varsayılan |
|----------|----------|------------|
| `OPENAI_API_KEY` | OpenAI API anahtarı | (zorunlu) |
| `OPENAI_MODEL` | Ana model | `gpt-4o` |
| `OPENAI_MINI_MODEL` | Küçük model | `gpt-4o-mini` |
| `BACKEND_HOST` | Backend host | `0.0.0.0` |
| `BACKEND_PORT` | Backend port | `8765` |
| `WATCH_PATHS` | İzlenecek klasörler (virgülle) | `~/Desktop,~/Documents` |

## 📝 Lisans

MIT
