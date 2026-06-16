# Promotion Gates — backtest → paper → live

## G1: Research → Paper
- [ ] >= 50 closed trades in backtest
- [ ] Profit factor > 1.2 after fees
- [ ] Max drawdown < 25%
- [ ] Walk-forward OOS positive (future phase)
- [ ] Strategy doc matches code

## G2: Paper start
- [ ] Binance Demo API keys configured
- [ ] Journal logging works
- [ ] Kill switch tested manually

## G3: Paper → Live (minimum 90 days paper)
- [ ] 90+ days paper without unexplained crashes
- [ ] Paper PnL within ±40% of backtest expectation
- [ ] Reconciliation: internal state = exchange state
- [ ] Every trade explainable from journal

## G4: Live deployment
- [ ] Start with 50% of paper position size
- [ ] `risk_per_trade` <= 0.5% in live.yaml
- [ ] Exchange-side stop (OCO) enabled
- [ ] Telegram alerts configured
- [ ] Capital = only what you can afford to lose

## G5: Scale capital
- [ ] 30+ days live, drawdown within limits
- [ ] Live profit factor > 1.0
- [ ] Scale +10% sizing per week if metrics hold
