"""Analisa consistência retorno total vs retorno mensal por estratégia."""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

LABELS = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]


def month_label(iso: str) -> str:
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return LABELS[dt.month - 1]


def monthly_from_trades(trades: list, initial: float) -> dict[str, float]:
    buckets: dict[str, float] = defaultdict(float)
    equity = initial
    for t in trades:
        m = month_label(t["exit_time"])
        buckets[m] += (t["pnl"] / equity) * 100 if equity else 0
        equity += t["pnl"]
    return dict(buckets)


def monthly_from_equity(equity: list) -> list[tuple[str, float, str]]:
    """Retorno % de cada mês calendário (equity fim/início do mês)."""
    by_month: dict[str, list] = defaultdict(list)
    for row in equity:
        ts = str(row.get("timestamp", row.get("day", "")))
        if len(ts) < 7:
            continue
        ym = ts[:7]
        by_month[ym].append(float(row["equity"]))

    out: list[tuple[str, float, str]] = []
    prev_end: float | None = None
    for ym in sorted(by_month.keys()):
        points = by_month[ym]
        start = prev_end if prev_end is not None else points[0]
        end = points[-1]
        ret = ((end / start) - 1) * 100 if start else 0
        year, month_num = ym.split("-")
        label = f"{LABELS[int(month_num) - 1]}/{year[2:]}"
        out.append((ym, ret, label))
        prev_end = end
    return out


def compound_pct(monthly_pcts: list[float]) -> float:
    factor = 1.0
    for r in monthly_pcts:
        factor *= 1 + r / 100
    return (factor - 1) * 100


def analyze(path: Path) -> dict:
    raw = json.loads(path.read_text(encoding="utf-8"))
    stats = raw["statistics"]
    trades = raw.get("trades", [])
    equity = raw.get("equity_curve", [])
    initial = float(equity[0]["equity"]) if equity else 10000.0
    final = float(equity[-1]["equity"]) if equity else initial
    total_report = float(stats["net_profit_pct"]) * 100
    total_equity = ((final / initial) - 1) * 100 if initial else 0
    trade_monthly = monthly_from_trades(trades, initial)
    cal_monthly = monthly_from_equity(equity) if equity else []
    cal_pcts = [r for _, r, _ in cal_monthly]
    cal_compound = compound_pct(cal_pcts)
    return {
        "file": path.name,
        "trades": len(trades),
        "total_report": round(total_report, 2),
        "total_equity": round(total_equity, 2),
        "cal_compound": round(cal_compound, 2),
        "sum_trade_monthly": round(sum(trade_monthly.values()), 2),
        "cal_monthly": [(label, round(r, 2)) for _, r, label in cal_monthly],
        "last_6": [(label, round(r, 2)) for _, r, label in cal_monthly[-6:]],
    }


def main() -> None:
    reports = sorted(Path("data/reports").glob("*_report.json"))
    print("=== Retorno total vs mensal (equity calendário) ===\n")
    print(f"{'Estratégia':42} Tr  Total%  CalMes%  Diff  OK")
    print("-" * 72)
    ok_count = 0
    for path in reports:
        a = analyze(path)
        name = a["file"].replace("_usdt_report.json", "")[:42]
        if a["trades"] == 0:
            print(f"{name:42}  0     0.0      0.0    0.0   —")
            continue
        diff = abs(a["total_report"] - a["cal_compound"])
        ok = diff <= 0.5
        if ok:
            ok_count += 1
        flag = "OK" if ok else "!!"
        print(
            f"{name:42} {a['trades']:2d} {a['total_report']:+7.1f} "
            f"{a['cal_compound']:+8.1f} {diff:5.2f}  {flag}"
        )

    print(f"\n{ok_count}/{sum(1 for p in reports if analyze(p)['trades'] > 0)} estratégias com retorno mensal batendo total (±0.5%)")

    print("\n=== Últimos 6 meses por estratégia (% real do mês) ===\n")
    for path in reports:
        a = analyze(path)
        if not a["cal_monthly"]:
            continue
        name = a["file"].replace("_usdt_report.json", "")
        months = ", ".join(f"{m}:{r:+.1f}%" for m, r in a["last_6"])
        print(f"{name}: {months}")


if __name__ == "__main__":
    main()
