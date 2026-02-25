# AutoCAD JARVIS — Proje Yapısı

## Genel Mimari

```
Ctrl+S (AutoCAD)
   │
   ▼
┌──────────────┐     WebSocket      ┌────────────────┐
│   watchdog   │ ──parse──broadcast──▶│  Next.js Panel │
│  File Watcher│                     │  (port 3000)   │
└──────┬───────┘                     └────────────────┘
       │                                     ▲
       ▼                                     │
┌──────────────┐     ┌───────────┐           │
│  DXF Parser  │────▶│  OpenAI   │───────────┘
│   (ezdxf)    │     │  gpt-4o   │  AI analiz sonucu
└──────────────┘     └───────────┘  WebSocket ile push
```

---

## Klasör Ağacı

```
autocad-jarvis/
│
├── .env.example              ← Ortam değişkenleri şablonu
├── .gitignore                ← Python, Node, misc ignore kuralları
├── README.md                 ← Kurulum ve kullanım rehberi
├── PROJECT_STRUCTURE.md      ← Bu dosya
│
├── backend/                  ← Python FastAPI (port 8765)
│   ├── main.py               ← Ana uygulama + REST endpoints + test DXF oluşturucu
│   ├── config.py             ← Pydantic BaseSettings (.env okur)
│   ├── requirements.txt      ← pip bağımlılıkları
│   ├── .env                  ← Gerçek ortam değişkenleri (git'e eklenmez)
│   │
│   ├── models/               ← Pydantic v2 veri şemaları
│   │   ├── __init__.py
│   │   ├── project.py        ← RoomModel, ProjectModel, AnalysisResult
│   │   └── websocket_message.py ← MessageType enum, WebSocketMessage
│   │
│   ├── core/                 ← İş mantığı katmanı
│   │   ├── __init__.py
│   │   ├── connection_manager.py ← WebSocket hub (multi-tab broadcast)
│   │   ├── dxf_parser.py     ← ezdxf ile DXF → ProjectModel dönüşümü
│   │   └── watcher.py        ← watchdog dosya izleyici (0.8s debounce)
│   │
│   ├── ai/                   ← Yapay zeka entegrasyonu
│   │   ├── __init__.py
│   │   └── openai_client.py  ← AsyncOpenAI wrapper (retry + fallback)
│   │
│   └── routers/              ← FastAPI endpoint'leri
│       ├── __init__.py
│       └── websocket.py      ← /ws WebSocket endpoint (ping/pong)
│
└── frontend/                 ← Next.js 14 App Router (port 3000)
    ├── package.json          ← Node bağımlılıkları
    ├── tsconfig.json         ← TypeScript strict mode
    ├── tailwind.config.ts    ← Tailwind + JARVIS renk paleti
    ├── next.config.mjs       ← Next.js ayarları
    ├── postcss.config.js     ← PostCSS (Tailwind entegrasyonu)
    │
    ├── app/                  ← Next.js App Router sayfaları
    │   ├── globals.css       ← Glassmorphism CSS tokens + animasyonlar
    │   ├── layout.tsx        ← Root layout (dark mode, lang="tr")
    │   └── page.tsx          ← Ana JARVIS panel sayfası (380px sağ panel)
    │
    ├── components/           ← React UI bileşenleri
    │   ├── ConnectionDot.tsx ← Yeşil/sarı/gri/kırmızı bağlantı göstergesi
    │   ├── StatusBar.tsx     ← Üst bar: logo + dosya adı + alan + durum
    │   ├── ProjectSummary.tsx← 2×2 istatistik grid + oda badge'leri
    │   └── AIInsightCard.tsx ← OpenAI Türkçe analiz kartı (3 durum: boş/loading/veri)
    │
    ├── hooks/                ← React custom hooks
    │   ├── useWebSocket.ts   ← WebSocket bağlantı + auto-reconnect + ping/pong
    │   └── useProjectState.tsx ← Global state (Context API, Zustand kullanılmaz)
    │
    └── lib/                  ← Paylaşılan yardımcılar
        ├── types.ts          ← TypeScript interface'leri (backend modelleriyle 1:1)
        └── constants.ts      ← WS_URL, API_URL, RECONNECT_DELAY sabitleri
```

---

## Backend Detayları

### REST Endpoints

| Method | Path | Açıklama |
|--------|------|----------|
| `GET` | `/health` | Sistem sağlık kontrolü (WS bağlantı, watcher, OpenAI durumu) |
| `POST` | `/watch` | Yeni klasör izlemeye ekle `{"path": "/abs/path"}` |
| `GET` | `/project/current` | Son parse edilen proje verisini döndür |
| `POST` | `/project/test` | Test DXF oluştur, parse et, WebSocket'e gönder |
| `WS` | `/ws` | WebSocket bağlantı noktası |
| `GET` | `/docs` | Swagger UI (otomatik) |

### WebSocket Mesaj Tipleri

| Tip | Yön | Açıklama |
|-----|-----|----------|
| `project_update` | Server → Client | DXF parse sonucu (ProjectModel) |
| `ai_analysis` | Server → Client | OpenAI analiz sonucu (AnalysisResult) |
| `watcher_status` | Server → Client | Dosya izleyici durum güncellemesi |
| `error` | Server → Client | Hata bildirimi |
| `ping` | Client → Server | Bağlantı canlılık kontrolü |
| `pong` | Server → Client | Ping yanıtı |

### Veri Akış Sırası

1. `watchdog` dosya değişikliğini algılar
2. 0.8s debounce sonrası `DXFParser.parse()` çağrılır
3. `ProjectModel` oluşturulur → `project_update` mesajı broadcast
4. `OpenAIClient.analyze_project()` çağrılır (async)
5. `AnalysisResult` döner → `ai_analysis` mesajı broadcast

### DXF Parse Mantığı

- **Odalar:** Kapalı `LWPOLYLINE` / `POLYLINE` → Shoelace formülü ile alan (min 4m²)
- **Duvarlar:** `LINE` / `LWPOLYLINE` — layer adında "WALL" veya "DUVAR" olanlar
- **Kapılar:** `INSERT` blokları — adında "DOOR" veya "KAPI" olanlar
- **Pencereler:** `INSERT` blokları — adında "WIND" veya "PENCERE" olanlar

---

## Frontend Detayları

### Panel Düzeni (380px, sağda sabit)

```
┌─────────────────────────────────┐
│ ⬡ JARVIS  │ dosya.dxf │ ● Bağlı│  ← StatusBar (56px)
├─────────────────────────────────┤
│ ┌────────┐  ┌────────┐         │
│ │ Alan   │  │ Oda    │         │  ← ProjectSummary
│ │ 124 m² │  │ 5      │         │     (2×2 stat grid)
│ ├────────┤  ├────────┤         │
│ │ Kapı   │  │ Duvar  │         │
│ │ 8      │  │ 78.4 m │         │
│ └────────┘  └────────┘         │
│                                │
│ [Salon 16.2m²] [Mutfak 9m²]   │  ← Oda badge'leri
│                                │
│ ┌─ ⬡ AI Analiz ──────────────┐│
│ │ Proje toplam 124.5m²...    ││  ← AIInsightCard
│ │ gpt-4o · 182 token         ││
│ └────────────────────────────┘│
│                                │
│ [📁 Klasör İzle]               │  ← Action buttons
│ [⚡ Test DXF Üret]             │
├─────────────────────────────────┤
│ Powered by gpt-4o  ● v1.0     │  ← Footer (32px)
└─────────────────────────────────┘
```

### State Yönetimi

- **Zustand/Redux yok** — `useState` + `React Context` kullanılır
- `useWebSocket` → WebSocket bağlantısı yönetir (reconnect, ping/pong)
- `useProjectState` → Mesaj tipine göre state günceller, Context ile dağıtır

### Auto-Reconnect Mekanizması

- Max deneme: 10
- Başlangıç gecikme: 3 saniye
- Exponential backoff: `delay × min(attempt, 5)` → max ~15 saniye
- Her bağlantıda ping interval: 15 saniye

---

## Ortam Değişkenleri

### Backend (`backend/.env`)

| Değişken | Varsayılan | Açıklama |
|----------|------------|----------|
| `OPENAI_API_KEY` | — | OpenAI API anahtarı (zorunlu, AI için) |
| `OPENAI_MODEL` | `gpt-4o` | Büyük projeler için model |
| `OPENAI_MINI_MODEL` | `gpt-4o-mini` | Küçük projeler için model |
| `BACKEND_HOST` | `0.0.0.0` | Sunucu adresi |
| `BACKEND_PORT` | `8765` | Sunucu portu |
| `LOG_LEVEL` | `INFO` | Log seviyesi |
| `WATCH_PATHS` | `~/Desktop,~/Documents` | İzlenecek klasörler |

### Frontend (`.env.local`)

| Değişken | Varsayılan |
|----------|------------|
| `NEXT_PUBLIC_WS_URL` | `ws://localhost:8765/ws` |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8765` |

---

## Bağımlılıklar

### Backend (Python)

| Paket | Amaç |
|-------|------|
| `fastapi` | Web framework + WebSocket |
| `uvicorn` | ASGI sunucu |
| `ezdxf` | DXF dosya okuma/yazma |
| `watchdog` | Dosya sistemi izleme |
| `openai` | OpenAI API istemcisi |
| `pydantic` | Veri doğrulama |
| `pydantic-settings` | .env dosyası yönetimi |

### Frontend (Node.js)

| Paket | Amaç |
|-------|------|
| `next` (14.x) | React framework (App Router) |
| `react` / `react-dom` | UI kütüphanesi |
| `tailwindcss` | CSS utility framework |
| `typescript` | Tip güvenliği |
