

"""
dashboard.py
------------
Camada de apresentação. Recebe DataFrames já tratados (ver tratamento.py)
e desenha os indicadores, gráficos e tabela no Streamlit.
"""
 
import pandas as pd
import plotly.express as px
import streamlit as st
 
from tratamento import calcular_indicadores, gerar_relatorio_texto
 
VERDE = "#2E7D5B"
VERDE_CLARO = "#8FCBAE"
VERDE_HOVER = "#256B4D"
CINZA_TEXTO = "#5B6470"
 
 
def aplicar_estilo():
    st.markdown(
        f"""
        <style>
        * {{
            color: #000000 !important;
        }}
        .stApp {{ background-color: #F4F6F5; }}
        .card {{
            background: #FFFFFF;
            border-radius: 16px;
            padding: 1.1rem 1.3rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.06);
            border: 1px solid #ECEFED;
        }}
        .kpi-label {{
            font-size: 0.82rem;
            margin-bottom: 0.15rem;
        }}
        .kpi-value {{
            font-size: 1.65rem;
            font-weight: 700;
        }}
        .kpi-badge {{
            display: inline-block;
            background: {VERDE};
            color: #FFFFFF !important;
            font-size: 0.72rem;
            font-weight: 600;
            padding: 0.1rem 0.5rem;
            border-radius: 999px;
            margin-left: 0.4rem;
        }}
        div[data-testid="stMetricValue"] {{ color: {VERDE} !important; }}
 
        div[data-testid="stPlotlyChart"] {{
            background: #FFFFFF;
            border-radius: 16px;
            padding: 0.9rem 1rem 0.4rem 1rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.06);
            border: 1px solid #ECEFED;
        }}
        div[data-testid="stDataFrame"] {{
            border-radius: 16px;
            overflow: hidden;
            border: 1px solid #ECEFED;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
 
 
def _kpi_card(label: str, value: str, badge: str | None = None):
    badge_html = f"<span class='kpi-badge'>{badge}</span>" if badge else ""
    st.markdown(
        f"""
        <div class="card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}{badge_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
 
 
def mostrar_indicadores(df: pd.DataFrame):
    ind = calcular_indicadores(df)
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        _kpi_card("Total de pilares", f"{ind['total_pilares']}")
    with col2:
        _kpi_card("Área total", f"{ind['area_total']:.3f} m²")
    with col3:
        _kpi_card("Área média", f"{ind['area_media']:.4f} m²")
    with col4:
        maior = ind["maior_pilar"]
        _kpi_card("Maior pilar", f"{maior['id']}" if maior else "-",
                   f"{maior['area']:.3f} m²" if maior else None)
    with col5:
        menor = ind["menor_pilar"]
        _kpi_card("Menor pilar", f"{menor['id']}" if menor else "-",
                   f"{menor['area']:.3f} m²" if menor else None)
 
 
def _tema_plotly(fig):
    fig.update_layout(
        font_family="Arial",
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=-0.25),
        hoverlabel=dict(
            bgcolor="white",
            font_color="#1C2B24",
            font_size=13,
            bordercolor=VERDE,
        ),
    )
    return fig
 
 
def grafico_area_por_pilar(df: pd.DataFrame):
    fig = px.bar(
        df.sort_values("ID"),
        x="ID",
        y="Área (m²)",
        color_discrete_sequence=[VERDE],
        text="Área (m²)",
    )
    fig.update_traces(
        texttemplate="%{text:.3f}",
        textposition="outside",
        marker=dict(cornerradius=8),
    )
    fig.update_yaxes(title="Área (m²)")
    fig.update_xaxes(title="Pilar")
    st.plotly_chart(_tema_plotly(fig), width='stretch')
 
 
def grafico_histograma(df: pd.DataFrame):
    fig = px.histogram(
        df,
        x="Área (m²)",
        nbins=10,
        color_discrete_sequence=[VERDE_CLARO],
    )
    fig.update_traces(
        marker_line_color=VERDE,
        marker_line_width=1,
        marker=dict(cornerradius=6),
    )
    fig.update_yaxes(title="Quantidade de pilares")
    st.plotly_chart(_tema_plotly(fig), width='stretch')
 
 
def grafico_pizza_setor(df: pd.DataFrame):
    contagem = df["Setor"].value_counts().reset_index()
    contagem.columns = ["Setor", "Quantidade"]
    fig = px.pie(
        contagem,
        names="Setor",
        values="Quantidade",
        hole=0.55,
        color_discrete_sequence=[VERDE, VERDE_CLARO, "#C9E4D6", VERDE_HOVER],
    )
    fig.update_traces(textinfo="percent+label", pull=[0.015] * len(contagem))
    st.plotly_chart(_tema_plotly(fig), width='stretch')
 
 
def tabela_filtravel(df: pd.DataFrame):
    setores = ["Todos"] + sorted(df["Setor"].dropna().unique().tolist())
    col_f1, col_f2 = st.columns([1, 2])
    with col_f1:
        setor_sel = st.selectbox("Filtrar por setor", setores)
    with col_f2:
        busca = st.text_input("Buscar por ID ou Nome", "")
 
    filtrado = df.copy()
    if setor_sel != "Todos":
        filtrado = filtrado[filtrado["Setor"] == setor_sel]
    if busca:
        busca_lower = busca.lower()
        filtrado = filtrado[
            filtrado["ID"].astype(str).str.lower().str.contains(busca_lower)
            | filtrado["Nome"].astype(str).str.lower().str.contains(busca_lower)
        ]
 
    st.dataframe(
        filtrado[["ID", "Nome", "Setor", "Base (cm)", "Largura (cm)", "Área (m²)"]],
        width='stretch',
        hide_index=True,
    )
    return filtrado
 
 
def botao_relatorio(df: pd.DataFrame, df_incompletos: pd.DataFrame, avisos: list[str]):
    relatorio = gerar_relatorio_texto(df, df_incompletos, avisos)
    st.download_button(
        "⬇ Gerar relatório resumido (.md)",
        data=relatorio,
        file_name="relatorio_pilares.md",
        mime="text/markdown",
    )
 
 
def mostrar_avisos(avisos: list[str], df_incompletos: pd.DataFrame):
    if avisos:
        with st.expander(f" Avisos do tratamento de dados ({len(avisos)})"):
            for a in avisos:
                st.write("•", a)
    if not df_incompletos.empty:
        with st.expander(f" Pilares pendentes de levantamento ({len(df_incompletos)})"):
            st.dataframe(df_incompletos, width='stretch', hide_index=True)
 








