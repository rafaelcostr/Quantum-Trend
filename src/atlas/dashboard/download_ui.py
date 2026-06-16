"""Helpers de download no dashboard Streamlit."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import streamlit as st


def download_bytes_button(
    label: str,
    data: bytes,
    file_name: str,
    *,
    mime: str,
    key: str,
    help_text: str | None = None,
    primary: bool = True,
) -> None:
    st.download_button(
        label,
        data=data,
        file_name=file_name,
        mime=mime,
        use_container_width=True,
        key=key,
        help=help_text,
        type="primary" if primary else "secondary",
    )


def download_file_button(
    label: str,
    path: Path,
    *,
    mime: str,
    key: str,
    help_text: str | None = None,
    primary: bool = False,
) -> None:
    if not path.is_file():
        st.error(f"Arquivo nao encontrado: {path.name}")
        return
    download_bytes_button(
        label,
        path.read_bytes(),
        path.name,
        mime=mime,
        key=key,
        help_text=help_text,
        primary=primary,
    )


def download_zip_button(label: str, zip_path: Path, *, key: str) -> None:
    if not zip_path.is_file():
        st.error(f"ZIP nao encontrado: {zip_path}")
        return
    download_file_button(
        label,
        zip_path,
        mime="application/zip",
        key=key,
        help_text="Relatorio unico + resumo + todos os individuais",
        primary=False,
    )


def open_folder_button(folder: Path, *, key: str) -> None:
    if st.button("Abrir pasta no Explorer", key=key, use_container_width=True):
        folder = folder.resolve()
        if sys.platform == "win32":
            os.startfile(folder)  # noqa: S606
        elif sys.platform == "darwin":
            subprocess.run(["open", str(folder)], check=False)
        else:
            subprocess.run(["xdg-open", str(folder)], check=False)


def show_export_result(project_root: Path, result: dict, *, key_prefix: str = "export") -> None:
    if not result.get("ok"):
        st.error(result.get("error", "Falha na exportacao."))
        return

    st.success(
        f"**{result['count']}** backtests exportados · "
        f"**{result['individual_count']}** relatorios individuais (.md)"
    )
    if result.get("errors"):
        for name, err in result["errors"]:
            st.warning(f"`{name}`: {err}")

    zip_path = Path(result["zip_path"])
    export_dir = Path(result["export_dir"])

    try:
        rel_zip = zip_path.relative_to(project_root)
        rel_exports = export_dir.relative_to(project_root)
        unified_path = Path(result.get("unified_path") or result.get("full_path") or "")
        rel_unified = unified_path.relative_to(project_root) if unified_path else "?"
        st.markdown(
            f"**Relatorio unico (IA):** `{rel_unified}`  \n"
            f"**ZIP:** `{rel_zip}`  \n"
            f"**Individuais:** `{rel_exports}`"
        )
    except ValueError:
        st.code(str(zip_path))

    unified_path = Path(result.get("unified_path") or result.get("full_path") or "")
    st.markdown("#### Relatorio unico para analise com IA")
    st.caption(
        "Um unico arquivo com **ranking + analise completa de todas as estrategias**. "
        "Cole no ChatGPT/Claude para comparar."
    )
    if unified_path.is_file():
        download_file_button(
            "BAIXAR RELATORIO UNICO PARA IA (.md)",
            unified_path,
            mime="text/markdown",
            key=f"{key_prefix}_dl_unified",
            help_text="Todas as estrategias em um so arquivo Markdown",
            primary=True,
        )
        with st.expander("Preview (inicio do relatorio)"):
            preview = unified_path.read_text(encoding="utf-8")[:6000]
            st.code(preview + ("\n\n..." if len(preview) >= 6000 else ""), language="markdown")
    else:
        st.warning("Relatorio unico nao encontrado. Clique em EXPORTAR TODOS novamente.")

    c1, c2 = st.columns(2)
    with c1:
        download_zip_button(
            "BAIXAR ZIP (tudo junto)",
            zip_path,
            key=f"{key_prefix}_dl_zip",
        )
    with c2:
        open_folder_button(export_dir, key=f"{key_prefix}_open_folder")

    st.markdown("#### Outros downloads")
    st.caption("Resumo curto ou cada estrategia separada.")

    summary_path = Path(result["summary_path"])
    full_path = unified_path

    cmp1, cmp2 = st.columns(2)
    with cmp1:
        download_file_button(
            "Resumo comparativo (.md)",
            summary_path,
            mime="text/markdown",
            key=f"{key_prefix}_dl_summary",
            help_text="So ranking e fichas resumidas",
        )
    with cmp2:
        if full_path.is_file():
            download_file_button(
                "Relatorio unico (.md) — copia",
                full_path,
                mime="text/markdown",
                key=f"{key_prefix}_dl_full",
                help_text="Mesmo arquivo do botao principal",
            )

    individuals = result.get("individual_files") or []
    if not individuals and export_dir.is_dir():
        individuals = [
            {"path": str(p), "file_name": p.name, "label": p.stem.replace("atlas_", "").replace("_", " ")}
            for p in sorted(export_dir.glob("*.md"))
        ]
    if individuals:
        with st.expander(f"Baixar cada estrategia separada ({len(individuals)})", expanded=False):
            for item in individuals:
                path = Path(item["path"])
                label = item.get("label") or path.name
                score = item.get("score")
                btn_label = f"{label} — Score {score:.0f}" if score is not None else label
                safe_key = path.stem.replace(".", "_")
                download_file_button(
                    btn_label,
                    path,
                    mime="text/markdown",
                    key=f"{key_prefix}_dl_{safe_key}",
                )

    st.caption(
        "Se algum botao nao baixar no navegador, use **Abrir pasta no Explorer** "
        "ou copie os arquivos de data/reports/."
    )


def save_report_markdown(project_root: Path, analysis, markdown: str) -> Path:
    """Salva relatorio individual em data/reports/exports/."""
    meta = analysis.metadata
    tf = str(meta.get("timeframe") or analysis.timeframe).lower()
    quote = str(meta.get("quote") or "usdt").lower()
    out_dir = project_root / "data" / "reports" / "exports"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"atlas_{analysis.strategy}_{tf}_{quote}.md"
    path.write_text(markdown, encoding="utf-8")
    return path
