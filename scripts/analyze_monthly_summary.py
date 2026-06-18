"""Resumo legível das 16 combinações oficiais (*_usdt_report.json)."""
from __future__ import annotations

from pathlib import Path

from analyze_monthly import analyze

REPORTS = Path(__file__).resolve().parents[1] / "data" / "reports"


def main() -> None:
    reports = sorted(REPORTS.glob("*_usdt_report.json"))
    print("ESTRATEGIA                          TF   Trades  Total%   Mensal bate?")
    print("-" * 68)
    ok = 0
    traded = 0
    for path in reports:
        a = analyze(path)
        stem = path.stem.replace("_usdt_report", "")
        strat, tf = stem.rsplit("_", 1)
        name = f"{strat[:28]:28} {tf:3}"
        if a["trades"] == 0:
            print(f"{name}    0      0.0%   sem trades")
            continue
        traded += 1
        diff = abs(a["total_report"] - a["cal_compound"])
        match = diff <= 0.5
        if match:
            ok += 1
        flag = "SIM" if match else f"NAO (diff {diff:.1f}%)"
        print(f"{name}  {a['trades']:3}  {a['total_report']:+6.1f}%   {flag}")

    print(f"\n{ok}/{traded} estrategias com trades batem retorno total vs soma mensal composta")

    print("\n--- % do mes (meses com |ret| >= 0.05%) ---")
    for path in reports:
        a = analyze(path)
        stem = path.stem.replace("_usdt_report", "")
        label = stem.replace("_", " ")
        active = [(m, r) for m, r in a["cal_monthly"] if abs(r) >= 0.05]
        if a["trades"] == 0:
            print(f"{label}: sem trades")
        elif not active:
            print(f"{label}: equity flat no periodo")
        else:
            txt = ", ".join(f"{m} {r:+.1f}%" for m, r in active)
            print(f"{label}: {txt}")


if __name__ == "__main__":
    main()
