# Quantum-Trend

Plataforma quantitativa para pesquisa, validação e operação automatizada em criptoativos.

Fluxo recomendado: **Backtest -> Walk-forward -> Paper -> Live**.

## Visão Geral

Quantum-Trend combina:

- Frontend React + TanStack Start.
- Backend Python Atlas + FastAPI.
- Broker Binance Demo/Live e broker Simulado local.
- Backtests com métricas profissionais, custos, comparação e laboratório quantitativo.
- Bot Paper/Live com reconciliação, kill switch, live gates, monitoramento e incidentes.

## Nomenclatura

| Termo      | Uso no projeto                                                        |
| ---------- | --------------------------------------------------------------------- |
| Paper      | Operação sem capital real, em Demo exchange ou broker Simulado local. |
| Demo       | Ambiente de corretora para Paper, como Binance Demo.                  |
| Live       | Operação com capital real.                                            |
| Backtest   | Simulação histórica.                                                  |
| Estratégia | Lógica que decide entrada, saída ou espera.                           |
| Relatório  | Resultado salvo de Backtest, validação ou análise.                    |
| Operação   | Ordem/trade executado ou registrado pelo bot.                         |

## Requisitos

- Node.js 22 recomendado.
- Python 3.11 ou 3.12.
- Git.
- Chaves Binance Demo para Paper em Demo exchange.
- Chaves Binance Live apenas para Live, depois dos gates.

## Instalação

```powershell
cd "C:\Users\HUNTER\Documents\PROJETOS\Quantum-Trend"

npm install

python -m venv .venv
.\.venv\Scripts\activate
pip install -e ".[dev]"

copy .env.example .env
```

Preencha no `.env`:

- `BINANCE_DEMO_API_KEY` e `BINANCE_DEMO_API_SECRET` para Paper em Binance Demo.
- `BINANCE_LIVE_API_KEY` e `BINANCE_LIVE_API_SECRET` somente para Live.
- `ATLAS_ALLOW_LIVE=1` somente quando for promover para Live.

## Como Rodar

Terminal 1, API Python:

```powershell
.\.venv\Scripts\activate
python -m atlas.cli api
```

Terminal 2, UI:

```powershell
npm run dev
```

Atalho:

```powershell
.\scripts\start.ps1
```

A UI usa proxy `/atlas-api -> http://127.0.0.1:8000/api`.

## Como Testar

Comando único:

```powershell
npm run check
```

Comandos separados:

```powershell
npm run check:frontend
npm run check:backend
npm run format
```

Validações executadas pelo CI:

- `npm run format:check`
- `npm run lint`
- `npx tsc --noEmit`
- `npm run build`
- `python -m pytest tests/ -q`

Para ativar o hook local de pré-commit:

```powershell
.\scripts\install-git-hooks.ps1
```

O hook roda Prettier automaticamente e lint antes do commit.

## Paper

Use Paper para observar execução sem capital real.

1. Configure `.env` com chaves Binance Demo ou use `exchange.id: simulated` para Paper local.
2. Rode a API e a UI.
3. Abra **Estratégias de Alta**, **Estratégias de Baixa** ou **Estratégias Laterais**.
4. Configure slots por ativo/timeframe.
5. Inicie Paper pelo Dashboard ou pela tela Operações.
6. Monitore Diário, Operações, Portfolio, Risco e Monitoramento.

## Promoção Para Live

Live deve ser tratado como etapa final, não como atalho.

Checklist mínimo:

1. Backtest aprovado.
2. Walk-forward aprovado.
3. Monte Carlo e robustez aceitáveis.
4. Paper estável pelo mínimo configurado.
5. Risco configurado.
6. Reconciliação saudável.
7. API e broker saudáveis.
8. Sem incidente operacional recente.
9. `ATLAS_ALLOW_LIVE=1`.
10. Confirmação textual forte na tela Live.

## Como Interpretar Métricas

| Métrica         | Interpretação                                                |
| --------------- | ------------------------------------------------------------ |
| Retorno total   | Resultado percentual do período simulado.                    |
| Max drawdown    | Maior queda do pico até o fundo. Menor é melhor.             |
| Sharpe          | Retorno ajustado à volatilidade.                             |
| Sortino         | Como Sharpe, penalizando mais o downside.                    |
| Calmar          | Retorno comparado ao drawdown máximo.                        |
| Profit factor   | Lucro bruto dividido por perda bruta. Acima de 1 é positivo. |
| Expectancy      | Expectativa média por operação.                              |
| Recovery factor | Capacidade de recuperar drawdown.                            |
| VaR/CVaR        | Estimativa de perda em cauda.                                |
| Robustez        | Score agregado de validação, estabilidade e risco.           |

## Principais Telas

- Dashboard: visão executiva do bot, saldo, regime e saúde.
- Backtests: execução individual e matriz 1H/4H/1D.
- Laboratório Quantitativo: experimentos, tags, replay e comparação.
- Resultados: análise visual dos Relatórios.
- Paper: validação antes de Live.
- Live: gates e confirmação para capital real.
- Operações: terminal em tempo real.
- Risco: limites de exposição, sizing, cooldown e perdas.
- Portfolio: exposição agregada, correlação e performance.
- Relatórios: consolidação histórica.

## CLI

```powershell
python -m atlas.cli backtest --config config/backtest_mm200_v2.yaml
python -m atlas.cli backtest-all
python -m atlas.cli research walkforward --config config/backtest_mm200_v2.yaml
python -m atlas.cli api
```

## Variáveis Importantes

| Variável                                           | Uso                         |
| -------------------------------------------------- | --------------------------- |
| `BINANCE_DEMO_API_KEY` / `BINANCE_DEMO_API_SECRET` | Paper em Binance Demo.      |
| `BINANCE_LIVE_API_KEY` / `BINANCE_LIVE_API_SECRET` | Live.                       |
| `ATLAS_ALLOW_LIVE=1`                               | Opt-in explícito para Live. |
| `ATLAS_LIVE_MIN_PAPER_DAYS=7`                      | Dias mínimos em Paper.      |
| `ATLAS_KILL_SWITCH=1`                              | Bloqueio global do bot.     |
| `TELEGRAM_*`                                       | Alertas Telegram.           |
| `DISCORD_WEBHOOK_URL`                              | Alertas Discord.            |
| `ALERT_WEBHOOK_URL`                                | Alertas Webhook.            |

## Documentação

- [Documentação técnica](docs/TECNICA.md)
- [Documentação operacional](docs/OPERACIONAL.md)
- [Qualidade e CI/CD](docs/QUALIDADE.md)

## Estrutura

```text
Quantum-Trend/
├── .github/workflows/      # CI/CD
├── .githooks/              # Hooks locais versionados
├── config/                 # Paper, Live e Backtests
├── data/                   # Cache, Relatórios e runtime local
├── docs/                   # Documentação técnica e operacional
├── scripts/                # Automação local
├── src/                    # Frontend React
├── src/atlas/              # Backend Python, bot, brokers e serviços
└── tests/                  # Testes Python
```

## CI/CD

O pipeline do GitHub Actions falha se formatação, lint, TypeScript, build ou testes Python falharem. Para bloquear merge, marque o job **Quality gate** como required nas regras de branch protection do GitHub.
