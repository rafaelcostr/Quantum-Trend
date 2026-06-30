# Documentação Operacional

## Rotina Recomendada

1. Rode `npm run check` antes de operar ou publicar alteração.
2. Inicie a API com `python -m atlas.cli api`.
3. Inicie a UI com `npm run dev`.
4. Verifique Dashboard, Monitoramento e Live gates.
5. Opere primeiro em Paper.
6. Promova para Live somente quando todos os gates estiverem verdes.

## Se A API Cair

Sintomas:

- UI mostra API offline.
- Endpoints retornam erro 502/503.
- Operações param de atualizar.

Ação:

```powershell
.\scripts\restart-api.ps1
```

Se a porta 8000 estiver ocupada:

```powershell
netstat -ano | findstr :8000
Stop-Process -Id <PID> -Force
python -m atlas.cli api
```

Depois confira:

- `GET /api/health`
- Dashboard
- Operações
- Monitoramento

## Se O Bot Travar

Sintomas:

- `last_tick_at` antigo.
- Bot aparece rodando, mas sem novas decisões.
- Incidente `bot_stopped` ou erro de runtime.

Ação:

1. Ative kill switch se houver risco operacional.
2. Pare o bot pela UI.
3. Confira incidentes em Monitoramento.
4. Reinicie a API se o stop não responder.
5. Inicie Paper novamente.
6. Só use Live se reconciliação e gates voltarem a ficar verdes.

## Se Uma Ordem Divergir Da Exchange

Sintomas:

- Posição local diferente da Binance.
- Ordem pendente esquecida.
- Incidente de reconciliação.

Ação:

1. Ative kill switch global.
2. Verifique posição real na exchange.
3. Rode reconciliação reiniciando o bot/API.
4. Confira Diário e Operações.
5. Resolva manualmente ordens pendentes na exchange, se necessário.
6. Só desative kill switch depois de estado local e exchange baterem.

## Como Ativar Kill Switch

Via `.env`:

```powershell
ATLAS_KILL_SWITCH=1
```

Via UI:

- Configurações -> Kill switch global.
- Kill switch por ativo.
- Kill switch por Estratégia.

Motivos comuns:

- API instável.
- Exchange indisponível.
- Divergência de posição.
- Drawdown alto.
- Ordem rejeitada em sequência.

## Como Restaurar Estado

Use reset apenas quando souber o impacto.

Pela UI:

- Configurações -> Reset do sistema.
- Escolha Relatórios, cache OHLCV ou dados Paper.

Manual:

- `data/runtime/` guarda estado de risco, incidentes e laboratório.
- `data/journal/` guarda journal fallback.
- `data/reports/` guarda Relatórios de Backtest.

Não apague dados de Live sem reconciliar com a exchange.

## Incidentes

Tipos comuns:

| Incidente                | Ação                                                |
| ------------------------ | --------------------------------------------------- |
| API sem resposta         | Reiniciar API e validar `/api/health`.              |
| Binance offline          | Pausar bot e aguardar recuperação.                  |
| Ordem rejeitada          | Conferir saldo, símbolo, lote mínimo e credenciais. |
| Saldo insuficiente       | Reduzir risco ou ajustar saldo.                     |
| Regime desatualizado     | Verificar conexão e cache de candles.               |
| Divergência com exchange | Ativar kill switch e reconciliar.                   |

## Promoção Para Live

Checklist operacional:

- Backtest aprovado.
- Walk-forward aprovado.
- Paper aprovado.
- Risco aprovado.
- Live gates aprovados.
- Monitoramento saudável.
- Sem incidente aberto crítico.
- Confirmação textual preenchida.

Live com incidente crítico aberto deve ser tratado como bloqueado.

## Pós-Operação

Ao encerrar:

1. Pare o bot.
2. Confira se não há ordem pendente.
3. Confira posição local e exchange.
4. Exporte ou revise Relatórios.
5. Registre observações no Laboratório Quantitativo.
