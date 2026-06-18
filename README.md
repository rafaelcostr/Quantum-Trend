# Quantum-Trend

Terminal quantitativo com **React + TanStack Start** no frontend e **Python Atlas + FastAPI** no backend.

Fluxo: **Backtest → Paper (Binance Demo) → Live**

## Requisitos

- Node.js 20+
- Python 3.11+
- Chaves [Binance Demo](https://demo.binance.com) para paper trading

## Instalação

```powershell
cd "C:\Users\HUNTER\Documents\PROJETOS\Quantum-Trend"

npm install

python -m venv .venv
.\.venv\Scripts\activate
pip install -e ".[dev]"

copy .env.example .env
# Preencha BINANCE_DEMO_API_KEY / BINANCE_DEMO_API_SECRET
```

## Desenvolvimento

**Terminal 1 — API Python (porta 8000):**

```powershell
.\.venv\Scripts\activate
python -m atlas.cli api
```

**Terminal 2 — UI React (porta 3000 ou 3001):**

```powershell
npm.cmd run dev
```

**Atalho (abre API + UI em dois terminais):**

```powershell
.\scripts\start.ps1
```

## Estratégias 1H, 4H e 1D

1. **Backtests** — escolha estratégia + gráfico **1H**, **4H** ou **1D**
2. **Estratégias** — até 3 slots paralelos (ex.: MM200 · 1H + MM200 · 4H + Range · 1D)
3. **Dashboard** — Iniciar Paper usa os slots habilitados (poll ~15s em 1H, 30s em 4H, 3600s em 1D)

Configs de backtest 1D: `config/backtest_mm200_v2_1d.yaml`, `config/backtest_daily_macro_1d.yaml`

A UI usa proxy **`/atlas-api` → `http://127.0.0.1:8000/api`** (configurado em `vite.config.ts` e `src/server.ts`).

> Se aparecer `WinError 10048`, a porta 8000 está ocupada. Feche a API antiga (`Ctrl+C`) ou:
> `netstat -ano | findstr :8000` → `Stop-Process -Id <PID> -Force`

## Docker (só API)

```powershell
docker compose up --build
```

## CLI

```powershell
# Backtest (uma estratégia ou todas)
python -m atlas.cli backtest --config config/backtest_mm200_v2.yaml
python -m atlas.cli backtest-all   # 11 estratégias × 1H + 4H + 1D

# Walk-forward (gate live)
python -m atlas.cli research walkforward --config config/backtest_mm200_v2.yaml

# Paper bot (via API POST /api/bot/start)
python -m atlas.cli api
```

## Variáveis `.env`

| Variável | Uso |
|----------|-----|
| `BINANCE_DEMO_API_*` | Paper trading (obrigatório para dados reais) |
| `BINANCE_LIVE_API_*` | Live (após gates) |
| `ATLAS_ALLOW_LIVE=1` | Opt-in explícito para live |
| `ATLAS_LIVE_MIN_PAPER_DAYS=7` | Dias mínimos em paper |
| `ATLAS_KILL_SWITCH=1` | Bloqueia bot |
| `TELEGRAM_*` | Alertas opcionais |

## Endpoints principais

| Rota | Descrição |
|------|-----------|
| `GET /api/health` | Status |
| `GET /api/dashboard` | Saldo demo real, equity, posições |
| `GET /api/operations/feed` | Feed de ticks/sinais |
| `GET /api/operations/stream` | SSE tempo real |
| `POST /api/bot/start` | Iniciar paper |
| `POST /api/bot/start-live` | Iniciar live (gates) |
| `GET /api/live/gates` | Checklist promoção |
| `POST /api/backtest` | Backtest |
| `POST /api/research/walkforward` | Walk-forward |
| `GET /api/validation` | Critérios demo |
| `PUT /api/risk` | Risco (sincroniza com engine) |

## Estrutura

```
Quantum-Trend/
├── src/                    # Frontend React (TanStack Start)
├── src/atlas/              # Engine Python
│   ├── api/                # FastAPI
│   ├── runtime/            # Bot, journal, gates
│   ├── services/           # Dashboard, demo, balance history
│   └── strategies/         # 8 estratégias
├── config/                 # paper.yaml, live.yaml, backtests
├── data/                   # journal, snapshots, reports (gitignored)
└── tests/                  # pytest
```

## Testes

```powershell
python -m pytest tests/ -q
npm run build
```

## Dados operacionais vs pesquisa

| Tela | Fonte de dados |
|------|----------------|
| Dashboard, Diário, Validação, Operações | **Binance Demo + journal** |
| Backtests, Resultados, Relatórios, IA | **Relatórios de backtest** |

## Live trading

1. Backtest + walk-forward
2. Paper ≥ 7 dias na demo
3. `ATLAS_ALLOW_LIVE=1` + chaves live
4. Todos os gates verdes em `/live`

Paper e live usam a mesma estratégia (`mm200_trend_v2`) em `config/paper.yaml` e `config/live.yaml`.
