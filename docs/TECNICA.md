# Documentação Técnica

## Arquitetura

Quantum-Trend é dividido em duas camadas principais:

- Frontend: React, TanStack Start, TanStack Router, TanStack Query, Tailwind e componentes locais.
- Backend: Python, FastAPI, engine Atlas, brokers, estratégias, serviços e armazenamento local em `data/`.

Fluxo principal:

```text
UI -> /api/* -> FastAPI -> services/runtime/research -> broker ou relatórios -> resposta JSON
```

## Módulos Principais

| Módulo                                    | Responsabilidade                                               |
| ----------------------------------------- | -------------------------------------------------------------- |
| `src/atlas/api/main.py`                   | Contratos HTTP e validação Pydantic.                           |
| `src/atlas/runtime/engine.py`             | Loop do bot Paper/Live.                                        |
| `src/atlas/runtime/bot_runner.py`         | Ciclo de vida, start/stop/restart e múltiplos slots.           |
| `src/atlas/runtime/live_gates.py`         | Gates de promoção para Live.                                   |
| `src/atlas/runtime/operational_safety.py` | Idempotência, kill switch e conflitos operacionais.            |
| `src/atlas/brokers/`                      | Interface de broker, Binance, Simulado e factory.              |
| `src/atlas/research/`                     | Backtest, métricas, relatórios e walk-forward.                 |
| `src/atlas/services/`                     | Payloads para UI, mercado, portfolio, laboratório e operações. |
| `src/atlas/monitoring/`                   | Healthcheck, incidentes e alertas.                             |
| `src/routes/`                             | Telas TanStack Router.                                         |
| `src/lib/api.ts`                          | Cliente HTTP tipado do frontend.                               |
| `src/lib/api-schemas.ts`                  | Validação Zod de respostas críticas.                           |

## Fluxo Do Bot

1. UI chama `POST /api/bot/start`.
2. `bot_runner` carrega slots e valida conflitos.
3. `TradingEngine` cria estratégia e broker pela factory.
4. O engine busca candles, calcula indicadores e monta contexto.
5. A estratégia devolve sinal: hold, entrada ou saída.
6. Gates operacionais validam kill switch, saúde, risco e reconciliação.
7. O broker executa ordem quando aprovado.
8. Journal, incidentes, alertas e runtime são atualizados.

A estratégia não executa ordem. Ela apenas decide. O broker executa.

## Fluxo De Backtest

1. UI ou CLI escolhe config, estratégia, timeframe e ativo.
2. `run_backtest_dashboard` resolve configuração.
3. O engine de pesquisa executa candles históricos.
4. Custos, slippage, spread, funding e lote mínimo são aplicados quando configurados.
5. Métricas profissionais são calculadas.
6. Relatório JSON é salvo em `data/reports/`.
7. UI consome os Relatórios em Backtests, Resultados e Laboratório Quantitativo.

## Fluxo De Live Gates

Live só deve iniciar quando `GET /api/live/gates` retorna elegível.

Gates principais:

- Paper mínimo.
- Drawdown dentro do limite.
- Reconciliação saudável.
- API saudável.
- Broker saudável.
- Risco configurado.
- Saldo mínimo.
- Sem erro operacional recente.
- `ATLAS_ALLOW_LIVE=1`.
- Confirmação textual forte.

## Contratos De Broker

O contrato central está em `src/atlas/brokers/base.py`.

Conceitos:

- `ExchangeId`: Binance, Simulado e placeholders Bybit/OKX/Coinbase.
- `MarketType`: Spot ou Futures.
- `BrokerVenue`: Paper local, Demo exchange ou Live exchange.
- `MarketSpec`: símbolo, base, quote, precisão, lote mínimo e notional mínimo.
- `BrokerCapabilities`: recursos suportados pelo broker.

Símbolos aceitos:

- `BTC/USDT`
- `BTCUSDT`
- `BTC_USDT`

Formato canônico interno: `BTC/USDT`.

## Contratos Da API

Endpoints principais:

| Endpoint                         | Contrato                                   |
| -------------------------------- | ------------------------------------------ |
| `GET /api/health`                | Status da API, bot e Binance Demo.         |
| `GET /api/dashboard`             | Visão agregada do terminal.                |
| `GET /api/markets`               | Tickers com cache e flag stale.            |
| `GET /api/markets/chart`         | Candles e indicadores por ativo/timeframe. |
| `POST /api/backtest`             | Executa Backtest individual.               |
| `POST /api/backtest/all`         | Executa matriz de Backtests.               |
| `GET /api/backtest/matrix`       | Lê matriz salva em Relatórios.             |
| `POST /api/research/walkforward` | Executa walk-forward.                      |
| `GET /api/live/gates`            | Checklist de promoção Live.                |
| `GET /api/monitoring/health`     | Painel de saúde e incidentes.              |
| `GET /api/quant-lab/experiments` | Experimentos versionados.                  |
| `POST /api/quant-lab/compare`    | Comparação multi-Backtest.                 |

## Dados Locais

| Caminho         | Conteúdo                                           |
| --------------- | -------------------------------------------------- |
| `data/reports/` | Relatórios de Backtest e validação.                |
| `data/cache/`   | OHLCV cacheado.                                    |
| `data/runtime/` | Estado local, incidentes, risco e laboratório.     |
| `data/journal/` | Journal fallback quando banco não está disponível. |

## Multi-Exchange

A etapa atual deixa a arquitetura pronta para novas exchanges:

1. Implementar broker em `src/atlas/brokers/<exchange>.py`.
2. Expor `spec`, `capabilities`, `market_spec`, `fetch_candles`, `get_balance`, `get_position`, `place_order` e `cancel_order`.
3. Registrar em `src/atlas/brokers/factory.py`.
4. Adicionar testes de contrato.
5. Adicionar configuração em `config/*.yaml`.

## Qualidade Técnica

Antes de abrir PR:

```powershell
npm run check
```

O CI repete os mesmos gates e falha em caso de erro.
