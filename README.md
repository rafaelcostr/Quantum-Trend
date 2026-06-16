# ATLAS QUANT

Plataforma modular de trading quantitativo em Python para **BTC/USDT spot (4H)**, com o mesmo núcleo de estratégia em três modos:

**Backtest → Paper → Live**

O projeto inclui pesquisa quantitativa, paper trading na Binance Demo, dashboard ao vivo e o módulo **ATLAS Intelligence** — análise automática em 3 níveis (decisão rápida, diagnóstico e research).

---

## Índice

1. [Requisitos](#requisitos)
2. [Instalação](#instalação)
3. [Configuração](#configuração)
4. [Início rápido](#início-rápido)
5. [Comandos CLI](#comandos-cli)
6. [ATLAS Intelligence](#atlas-intelligence)
7. [Estratégias](#estratégias)
8. [Arquitetura](#arquitetura)
9. [Dashboard](#dashboard)
10. [Alertas Telegram](#alertas-telegram)
11. [Promoção Backtest → Paper → Live](#promoção-backtest--paper--live)
12. [Testes](#testes)
13. [Roadmap](#roadmap)

---

## Requisitos

- **Python 3.11+**
- **Windows / Linux / macOS**
- Conta **Binance Demo** para paper trading ([demo.binance.com](https://demo.binance.com))
- **Docker** (opcional) para PostgreSQL e journal persistente
- **Telegram** (opcional) para alertas

---

## Instalação

```powershell
# Clone ou entre na pasta do projeto
cd "C:\Users\CRIPTOCRATA\projects\Quantum Trend"

# Ambiente virtual
python -m venv .venv
.\.venv\Scripts\activate

# Instalar pacote + dependências de desenvolvimento
pip install -e ".[dev]"
```

---

## Configuração

### 1. Arquivo `.env`

```powershell
copy .env.example .env
```

Edite `.env`:

```env
# PostgreSQL (Docker ATLAS usa porta 15432 no host)
DATABASE_URL=postgresql://atlas:atlas@localhost:15432/atlas_quant

# Binance Demo — paper trading
BINANCE_DEMO_API_KEY=sua_chave
BINANCE_DEMO_API_SECRET=seu_secret

# Telegram (opcional)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

**Importante:**
- Crie as chaves em **https://demo.binance.com** (não na Binance real).
- Habilite **Leitura + Trading Spot** e restrinja ao seu **IP público**.
- Nunca coloque chaves reais em `.env.example` ou no Git.

### 2. PostgreSQL (opcional)

```powershell
docker compose up -d
```

O container `atlas_postgres` expõe a porta **15432** (evita conflito com Postgres local na 5432).

Se já tiver Postgres na máquina, aponte `DATABASE_URL` para ele e rode `database/migrations/001_initial.sql`.

---

## Início rápido

```powershell
# 1. Baixar dados históricos BTC/USDT 4H
atlas research download

# 2. Rodar backtest (estratégia padrão)
atlas research backtest

# 3. Comparar todas as estratégias (Atlas Score)
atlas research compare

# 3b. Walk-forward (IS/OOS) para Nível 3
atlas research walkforward --config config/backtest_v2_2.yaml

# 4. Validar API Binance Demo
atlas trade check

# 5. Paper trading (um tick)
atlas trade paper --once

# 6. Dashboard web
atlas dashboard
```

Abra **http://localhost:8501** → sidebar → **ATLAS Intelligence**.

---

## Comandos CLI

### Pesquisa (`atlas research`)

| Comando | Descrição |
|---------|-----------|
| `atlas research download` | Baixa OHLCV via CCXT, cache Parquet |
| `atlas research backtest --config config/backtest_mm200_v2.yaml` | Backtest event-driven |
| `atlas research compare` | Ranking de estratégias por **Atlas Score** |
| `atlas research walkforward --config config/backtest_v2_2.yaml` | Walk-forward 70/30 IS/OOS + JSON para Nível 3 |

### Operação (`atlas trade`)

| Comando | Descrição |
|---------|-----------|
| `atlas trade check` | Testa chave demo, IP, saldo |
| `atlas trade paper` | Loop 24/7 na Binance Demo |
| `atlas trade paper --once` | Um único ciclo de avaliação |
| `atlas trade live` | Live (com confirmação — use só após gates) |

### Monitoramento

| Comando | Descrição |
|---------|-----------|
| `atlas alerts test` | Envia mensagem de teste no Telegram |
| `atlas dashboard` | Dashboard Streamlit (trading + intelligence) |

---

## ATLAS Intelligence

Sistema de análise em **3 níveis** (funil: decisão rápida → diagnóstico → research).

### Nível 1 — Decisão rápida (~10 segundos)

- **Atlas Score** (0–100)
- Drawdown, Profit Factor, Expectância, Sharpe, Retorno, Trades
- Nível de confiança e risco de overfitting
- Pontos fortes / fracos / riscos
- Checklist BACKTEST → PAPER
- Botão **Copiar Relatório para IA** (Markdown)

**Pesos do Atlas Score:**

| Componente | Peso |
|------------|------|
| Drawdown | 25% |
| Profit Factor | 25% |
| Expectância | 15% |
| Sharpe | 15% |
| Retorno | 10% |
| Trades | 5% |
| Confiança | 5% |

| Score | Classificação |
|-------|---------------|
| 90–100 | Excelente |
| 80–89 | Muito Bom |
| 70–79 | Promissor |
| 60–69 | Precisa Melhorar |
| <60 | Rejeitado |

### Nível 2 — Diagnóstico (Sprint 2 ✅)

Métricas intermediárias com explicação educacional:

- Sortino Ratio
- Recovery Factor
- Payoff Ratio
- Calmar Ratio
- Exposição ao mercado
- Maior sequência de ganhos / perdas
- **Diagnóstico automático** em linguagem natural

Cada métrica inclui: *O que é · Por que importa · Faixas · Semáforo*

### Nível 3 — Research Lab (Sprint 3 ✅)

Engines de robustez estatística:

- **Walk-forward** — split 70% in-sample / 30% out-of-sample
- **Monte Carlo** — bootstrap de trades (P5 retorno, P95 drawdown)
- **OOS** — retorno, Sharpe e Profit Factor fora da amostra
- **Kelly**, **Ulcer Index**, **Skewness/Kurtosis**
- **Research Interpreter** — diagnóstico automático IS vs OOS
- **Detector de overfitting** completo (L3)

```powershell
atlas research walkforward --config config/backtest_v2_2.yaml
atlas dashboard   # aba Nível 3 — Research
```

Salva `data/reports/{estrategia}_walkforward.json`; o dashboard e o relatório IA carregam automaticamente.

---

## Estratégias

| Nome | Tipo |
|------|------|
| `range_hunter_v1` | Mean reversion (BB + RSI + ADX) |
| `range_hunter_v2` | v1 + suporte/resistência |
| `bb_squeeze_v1` | Squeeze + breakout |
| `regime_switching_v1` | Range + trend (trend opcional) |
| `mm200_trend_v1` | Long acima da MM200 |
| `mm200_trend_v2` | Crossover MM200 |
| `mm200_daily_macro_v1` | Crossover + filtro macro diário |
| `portfolio_macro_micro_v1` | Macro 70% + micro range 30% |

Configs em `config/backtest_*.yaml` e `config/paper.yaml`.

Registrar nova estratégia em `src/atlas/strategies/registry.py`.

---

## Arquitetura

```
src/atlas/
├── core/              # modelos, indicadores, risk, config YAML
├── strategies/        # lógica de sinal (pura)
├── brokers/           # simulado, Binance demo/live (CCXT)
├── research/          # coleta, backtester, estatísticas
├── intelligence/      # Atlas Score, diagnóstico L1/L2, relatório IA
├── runtime/           # engine, runner, journal
├── dashboard/         # Streamlit + TradingView + Intelligence UI
├── monitoring/        # Telegram + watchdog (sinal/DD)
└── cli.py
```

### Fluxo de dados

```
Estratégia → Backtester/Paper Engine → Journal / Reports JSON
                                              ↓
                                    ATLAS Intelligence
                                              ↓
                                    Dashboard + Relatório IA
```

### Indicadores disponíveis

Bollinger Bands, RSI, ADX, ATR, MM20/200, suporte/resistência, macro diário (`macro_bull`).

### Backtester

- Event-driven, fees 0,1%, slippage 0,05%
- Entrada no próximo open
- Warmup ~205 barras
- Relatórios em `data/reports/*_report.json`

---

## Dashboard

```powershell
atlas dashboard
```

**Trading ao Vivo:**
- Gráfico TradingView ou Plotly (candles, MM20/200, BB)
- Marcadores de entrada/saída
- PnL, drawdown, journal
- Auto-refresh

**ATLAS Intelligence:**
- Abas Nível 1 / 2 / 3
- Seletor de estratégia (relatórios de backtest)
- Download e cópia de relatório Markdown

---

## Alertas Telegram

Configure `TELEGRAM_BOT_TOKEN` e `TELEGRAM_CHAT_ID` no `.env`.

```powershell
atlas alerts test
```

O bot envia alertas para:
- Início do runner
- Entrada / saída executada
- Sinal `enter_long` / `exit_long` **sem ordem**
- Drawdown acima do limite (`drawdown_alert_pct` em `config/paper.yaml`)
- Erros do loop

---

## Promoção Backtest → Paper → Live

Critérios documentados em `docs/promotion_gates.md`. Resumo:

**Backtest → Paper**
- PF ≥ 1,3 · DD ≤ 25% · Sharpe ≥ 1,0 · ≥ 50 trades
- Walk-forward (futuro)

**Paper → Live**
- 90+ dias de paper estável
- Reconciliação com exchange
- Drawdown dentro do limite

O checklist aparece automaticamente no **Nível 1** do Intelligence.

---

## Testes

```powershell
pytest tests -q
```

Cobertura: risk, backtester, estratégias, alerts, watchdog, intelligence L1/L2/L3.

---

## Roadmap

| Sprint | Status | Conteúdo |
|--------|--------|----------|
| Core + backtest + paper | ✅ | Engine, Binance Demo, journal |
| Dashboard ao vivo | ✅ | TradingView, PnL, marcadores |
| Intelligence Nível 1 | ✅ | Score, semáforos, relatório IA, compare |
| Intelligence Nível 2 | ✅ | Sortino, Recovery, diagnóstico educacional |
| Intelligence Nível 3 | ✅ | Walk-forward, Monte Carlo, OOS, Research Lab |
| Produção | 🔜 | Persistência posição, reconciliação, CI/CD |

---

## Estrutura de pastas

```
Quantum Trend/
├── config/           # YAML por estratégia e modo
├── data/
│   ├── cache/        # Parquet OHLCV
│   └── reports/      # JSON de backtest
├── database/         # Migrations SQL
├── docs/             # Estratégia e promotion gates
├── scripts/          # Utilitários (ex.: check_binance_demo.py)
├── src/atlas/        # Código principal
├── tests/
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

---

## Aviso legal

Este software é para **educação e pesquisa quantitativa**. Trading envolve risco de perda total. Resultados de backtest **não garantem** performance futura. Use paper trading extensivo antes de considerar capital real. O autor não se responsabiliza por perdas financeiras.

---

## Licença e contribuição

Projeto em desenvolvimento ativo. Consulte `docs/strategy_v1.md` para a lógica da estratégia principal e `docs/promotion_gates.md` para critérios de promoção entre ambientes.
