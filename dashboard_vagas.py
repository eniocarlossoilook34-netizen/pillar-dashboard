"""
dashboard_vagas.py
-------------------
Camada de apresentação do módulo de Vagas de Estacionamento: indicadores
estatísticos (média, desvio padrão), gráficos de real vs. projeto e
tabela de conformidade.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard import VERDE, VERDE_CLARO, CINZA_TEXTO, _kpi_card, _tema_plotly
from tratamento_vagas import calcular_indicadores_vagas

FORA_PADRAO = "#D64545"


def mostrar_indicadores_vagas(df: pd.DataFrame):
    ind = calcular_indicadores_vagas(df)
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        _kpi_card("Total de vagas", f"{ind['total_vagas']}")
    with col2:
        _kpi_card("Área total", f"{ind['area_total']:.2f} m²")
    with col3:
        _kpi_card("Desvio padrão - Base", f"{ind['base_desvio_padrao']:.1f} cm")
    with col4:
        _kpi_card("Desvio padrão - Altura", f"{ind['altura_desvio_padrao']:.1f} cm")
    with col5:
        _kpi_card(
            "Fora do padrão",
            f"{ind['qtd_fora_padrao']} / {ind['total_vagas']}",
        )
    return ind


def grafico_dispersao_real_vs_projeto(df: pd.DataFrame, ind: dict):
    fig = px.scatter(
        df,
        x="Base real (cm)",
        y="Altura real (cm)",
        color="Dentro do padrão",
        color_discrete_map={True: VERDE, False: FORA_PADRAO},
        hover_name="ID",
        labels={"Dentro do padrão": "Dentro do padrão"},
    )
    fig.add_trace(
        go.Scatter(
            x=[ind["base_projeto"]],
            y=[ind["altura_projeto"]],
            mode="markers+text",
            marker=dict(symbol="x", size=14, color="#1C2B24", line=dict(width=2)),
            text=["Projeto"],
            textposition="top center",
            name="Especificação de projeto",
        )
    )
    fig.update_xaxes(title="Base real (cm)")
    fig.update_yaxes(title="Altura real (cm)")
    st.plotly_chart(_tema_plotly(fig), width="stretch")


def grafico_desvio_por_vaga(df: pd.DataFrame):
    ordenado = df.sort_values("Desvio Área (%)")
    fig = px.bar(
        ordenado,
        x="ID",
        y="Desvio Área (%)",
        color="Dentro do padrão",
        color_discrete_map={True: VERDE, False: FORA_PADRAO},
    )
    fig.update_traces(marker=dict(cornerradius=6))
    fig.update_yaxes(title="Desvio de área vs. projeto (%)")
    fig.update_xaxes(title="Vaga")
    fig.add_hline(y=0, line_color="#1C2B24", line_width=1)
    st.plotly_chart(_tema_plotly(fig), width="stretch")


def grafico_distribuicao_desvio(df: pd.DataFrame):
    fig = px.histogram(
        df,
        x="Desvio Área (%)",
        nbins=10,
        color_discrete_sequence=[VERDE_CLARO],
    )
    fig.update_traces(marker_line_color=VERDE, marker_line_width=1, marker=dict(cornerradius=6))
    fig.add_vline(x=0, line_color="#1C2B24", line_width=1, line_dash="dash")
    fig.update_yaxes(title="Quantidade de vagas")
    fig.update_xaxes(title="Desvio de área vs. projeto (%)")
    st.plotly_chart(_tema_plotly(fig), width="stretch")


def tabela_vagas(df: pd.DataFrame):
    setores = ["Todas"] + sorted(df["Setor"].dropna().unique().tolist())
    col_f1, col_f2 = st.columns([1, 2])
    with col_f1:
        setor_sel = st.selectbox("Filtrar por setor", setores, key="setor_vagas")
    with col_f2:
        so_fora = st.checkbox("Mostrar só as fora do padrão")

    filtrado = df.copy()
    if setor_sel != "Todas":
        filtrado = filtrado[filtrado["Setor"] == setor_sel]
    if so_fora:
        filtrado = filtrado[~filtrado["Dentro do padrão"]]

    colunas = [
        "ID", "Setor",
        "Base real (cm)", "Base projeto (cm)", "Desvio Base (%)",
        "Altura real (cm)", "Altura projeto (cm)", "Desvio Altura (%)",
        "Área real (m²)", "Área projeto (m²)", "Desvio Área (%)",
        "Dentro do padrão",
    ]
    st.dataframe(filtrado[colunas], width="stretch", hide_index=True)
    return filtrado


def mostrar_avisos_vagas(avisos: list[str], df_incompletos: pd.DataFrame):
    if avisos:
        with st.expander(f" Avisos do tratamento de dados ({len(avisos)})"):
            for a in avisos:
                st.write("•", a)
    if not df_incompletos.empty:
        with st.expander(f" Vagas com dados incompletos ({len(df_incompletos)})"):
            st.dataframe(df_incompletos, width="stretch", hide_index=True)
