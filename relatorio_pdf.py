"""
relatorio_pdf.py
-----------------
Gera o relatório consolidado em PDF (Pilares + Vagas de Estacionamento),
com indicadores, gráficos estáticos e a tabela de conformidade real vs.
projeto. Usa reportlab (texto/tabelas) + matplotlib (gráficos), sem
depender de nenhum binário externo - funciona só com pip install.
"""

import io
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak,
)

from tratamento import calcular_indicadores
from tratamento_vagas import calcular_indicadores_vagas

VERDE = "#2E7D5B"
FORA_PADRAO = "#D64545"
CINZA = "#5B6470"
FUNDO_LINHA = "#F4F6F5"
BORDA = "#ECEFED"


def _estilos():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("TituloRel", parent=styles["Title"], textColor=colors.HexColor(VERDE)))
    styles.add(ParagraphStyle(
        "SecaoRel", parent=styles["Heading2"], textColor=colors.HexColor(VERDE),
        spaceBefore=14, spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        "AvisoRel", parent=styles["Normal"], textColor=colors.HexColor(CINZA),
        fontSize=9, leading=12,
    ))
    styles.add(ParagraphStyle("CelulaRel", parent=styles["Normal"], fontSize=9, leading=11))
    styles.add(ParagraphStyle(
        "CabecalhoRel", parent=styles["Normal"], fontSize=9, leading=11,
        textColor=colors.white, fontName="Helvetica-Bold",
    ))
    styles.add(ParagraphStyle("CelulaPequena", parent=styles["Normal"], fontSize=7.5, leading=9))
    styles.add(ParagraphStyle(
        "CabecalhoPequeno", parent=styles["Normal"], fontSize=7.5, leading=9,
        textColor=colors.white, fontName="Helvetica-Bold",
    ))
    return styles


def _txt(valor, estilo) -> Paragraph:
    """Célula de tabela como Paragraph - necessário para o m² renderizar
    certo (superíndice via tag <super>, nunca o caractere Unicode ²,
    que os fontes padrão do reportlab não desenham - ver SKILL.md do pdf)."""
    s = str(valor).replace("m²", "m<super>2</super>")
    return Paragraph(s, estilo)


def _fig_para_imagem(fig, largura_cm=16, proporcao=0.45):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=160, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return Image(buf, width=largura_cm * cm, height=largura_cm * cm * proporcao)


def _grafico_area_por_pilar(df: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(8, 3.6))
    ordenado = df.sort_values("ID")
    ax.bar(ordenado["ID"], ordenado["Área (m²)"], color=VERDE)
    ax.set_ylabel("Área (m²)")
    ax.set_xlabel("Pilar")
    ax.tick_params(axis="x", rotation=90, labelsize=6)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    return fig


def _grafico_desvio_vagas(df: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(8, 3.6))
    ordenado = df.sort_values("Desvio Área (%)")
    cores = [VERDE if ok else FORA_PADRAO for ok in ordenado["Dentro do padrão"]]
    ax.bar(ordenado["ID"], ordenado["Desvio Área (%)"], color=cores)
    ax.axhline(0, color="#1C2B24", linewidth=1)
    ax.set_ylabel("Desvio de área vs. projeto (%)")
    ax.set_xlabel("Vaga")
    ax.tick_params(axis="x", rotation=90, labelsize=6)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    return fig


def _tabela_kv(linhas, styles):
    cabecalho, *corpo = linhas
    linhas_p = [[_txt(c, styles["CabecalhoRel"]) for c in cabecalho]]
    linhas_p += [[_txt(c, styles["CelulaRel"]) for c in linha] for linha in corpo]
    t = Table(linhas_p, colWidths=[8 * cm, 8 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(VERDE)),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor(BORDA)),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor(FUNDO_LINHA)]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def _secao_pilares(story, styles, df_pilares: pd.DataFrame, avisos: list[str]):
    ind = calcular_indicadores(df_pilares)
    story.append(Paragraph("1. Pilares", styles["SecaoRel"]))
    linhas = [
        ["Indicador", "Valor"],
        ["Total de pilares", str(ind["total_pilares"])],
        ["Área total", f"{ind['area_total']:.3f} m²"],
        ["Área média", f"{ind['area_media']:.4f} m²"],
        ["Maior pilar", f"{ind['maior_pilar']['id']} ({ind['maior_pilar']['area']:.4f} m²)"],
        ["Menor pilar", f"{ind['menor_pilar']['id']} ({ind['menor_pilar']['area']:.4f} m²)"],
        ["Setores distintos", str(ind["qtd_setores"])],
    ]
    story.append(_tabela_kv(linhas, styles))
    story.append(Spacer(1, 10))
    story.append(_fig_para_imagem(_grafico_area_por_pilar(df_pilares)))
    if avisos:
        story.append(Spacer(1, 8))
        story.append(Paragraph("Observações do tratamento de dados:", styles["Heading4"]))
        for a in avisos:
            story.append(Paragraph("• " + a, styles["AvisoRel"]))


def _secao_vagas(story, styles, df_vagas: pd.DataFrame, avisos: list[str]):
    ind = calcular_indicadores_vagas(df_vagas)
    story.append(Paragraph("2. Vagas de Estacionamento — Real vs. Projeto", styles["SecaoRel"]))
    linhas = [
        ["Indicador", "Valor"],
        ["Total de vagas", str(ind["total_vagas"])],
        ["Área total (real)", f"{ind['area_total']:.2f} m²"],
        ["Base — média / desvio padrão", f"{ind['base_media']:.1f} cm / {ind['base_desvio_padrao']:.1f} cm"],
        ["Altura — média / desvio padrão", f"{ind['altura_media']:.1f} cm / {ind['altura_desvio_padrao']:.1f} cm"],
        ["Desvio médio de Base vs. projeto", f"{ind['desvio_base_pct_medio']:.1f}%"],
        ["Desvio médio de Altura vs. projeto", f"{ind['desvio_altura_pct_medio']:.1f}%"],
        ["Vagas dentro do padrão", f"{ind['qtd_dentro_padrao']} / {ind['total_vagas']}"],
        ["Maior desvio individual", f"{ind['vaga_maior_desvio']['id']} ({ind['vaga_maior_desvio']['desvio_pct']:.1f}%)"],
        ["Especificação de projeto", f"Base {ind['base_projeto']:.0f} cm x Altura {ind['altura_projeto']:.0f} cm"],
    ]
    story.append(_tabela_kv(linhas, styles))
    story.append(Spacer(1, 10))
    story.append(_fig_para_imagem(_grafico_desvio_vagas(df_vagas)))
    if avisos:
        story.append(Spacer(1, 8))
        story.append(Paragraph("Observações do tratamento de dados:", styles["Heading4"]))
        for a in avisos:
            story.append(Paragraph("• " + a, styles["AvisoRel"]))

    story.append(PageBreak())
    story.append(Paragraph("Tabela completa — Real vs. Projeto", styles["SecaoRel"]))
    cabecalho = [
        "ID", "Base real", "Base proj.", "Desv. Base",
        "Altura real", "Altura proj.", "Desv. Altura", "Dentro?",
    ]
    linhas_tab = [[_txt(c, styles["CabecalhoPequeno"]) for c in cabecalho]]
    for _, r in df_vagas.sort_values("ID").iterrows():
        linhas_tab.append([_txt(v, styles["CelulaPequena"]) for v in [
            r["ID"],
            f"{r['Base real (cm)']:.1f}",
            f"{r['Base projeto (cm)']:.0f}",
            f"{r['Desvio Base (%)']:.1f}%",
            f"{r['Altura real (cm)']:.1f}",
            f"{r['Altura projeto (cm)']:.0f}",
            f"{r['Desvio Altura (%)']:.1f}%",
            "Sim" if r["Dentro do padrão"] else "Não",
        ]])
    tabela = Table(linhas_tab, repeatRows=1)
    tabela.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(VERDE)),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor(BORDA)),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor(FUNDO_LINHA)]),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(tabela)


def _rodape(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor(CINZA))
    canvas.drawString(1.8 * cm, 1.2 * cm, "Dashboard de Pilares e Vagas - relatório gerado automaticamente")
    canvas.drawRightString(A4[0] - 1.8 * cm, 1.2 * cm, f"Página {doc.page}")
    canvas.restoreState()


def gerar_pdf(
    df_pilares: pd.DataFrame | None = None,
    avisos_pilares: list[str] | None = None,
    df_vagas: pd.DataFrame | None = None,
    avisos_vagas: list[str] | None = None,
) -> bytes:
    """Monta o PDF e retorna os bytes prontos para um st.download_button."""
    buffer = io.BytesIO()
    styles = _estilos()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=1.8 * cm, bottomMargin=1.8 * cm,
        leftMargin=1.8 * cm, rightMargin=1.8 * cm,
    )

    story = [
        Paragraph("Relatório de Inspeção Estrutural", styles["TituloRel"]),
        Paragraph(datetime.now().strftime("Gerado em %d/%m/%Y às %H:%M"), styles["AvisoRel"]),
        Spacer(1, 14),
    ]

    tem_pilares = df_pilares is not None and not df_pilares.empty
    tem_vagas = df_vagas is not None and not df_vagas.empty

    if tem_pilares:
        _secao_pilares(story, styles, df_pilares, avisos_pilares or [])
    if tem_pilares and tem_vagas:
        story.append(PageBreak())
    if tem_vagas:
        _secao_vagas(story, styles, df_vagas, avisos_vagas or [])

    if not tem_pilares and not tem_vagas:
        story.append(Paragraph("Nenhum dado disponível para gerar o relatório.", styles["Normal"]))

    doc.build(story, onFirstPage=_rodape, onLaterPages=_rodape)
    return buffer.getvalue()
