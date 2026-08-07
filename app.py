"""
app.py
------
Ponto de entrada do dashboard. Rode com:

    python -m streamlit run app.py
"""

from pathlib import Path

import streamlit as st

import dashboard
import dashboard_vagas
from tratamento import carregar_planilha, tratar_dados
from tratamento_vagas import carregar_vagas, tratar_vagas
from relatorio_pdf import gerar_pdf

CAMINHO_PADRAO = Path(__file__).parent / "data" / "pilares_V2.xlsx"

st.set_page_config(
    page_title="Dashboard de Pilares e Vagas",
    page_icon="🏗️",
    layout="wide",
)

dashboard.aplicar_estilo()

with st.sidebar:
    st.title(" Obra")
    st.caption("Ferramenta de apoio à inspeção estrutural")
    arquivo = st.file_uploader("Enviar planilha (.xlsx)", type=["xlsx"])
    st.caption(
        "Uma aba com colunas ID, Nome, Setor, Base (cm), Largura (cm) para os "
        "pilares, e uma aba com 'vagas' no nome para as vagas de estacionamento. "
        "Sem upload, usa data/pilares_V2.xlsx como exemplo."
    )

st.markdown("## Bem-vindo(a) — Dashboard da Obra")
st.caption("Tratamento automático de dados, indicadores, estatística e relatório em PDF.")

origem = arquivo if arquivo is not None else CAMINHO_PADRAO

# --- Pilares -----------------------------------------------------------
pilares_ok = False
try:
    df_pilares_bruto = carregar_planilha(origem)
    df_pilares, pilares_incompletos, avisos_pilares = tratar_dados(df_pilares_bruto)
    pilares_ok = not df_pilares.empty
except Exception as e:
    df_pilares, pilares_incompletos, avisos_pilares = None, None, []
    st.sidebar.warning(f"Pilares: não foi possível ler ({e})")

# --- Vagas de estacionamento --------------------------------------------
vagas_ok = False
try:
    df_vagas_bruto = carregar_vagas(origem)
    df_vagas, vagas_incompletos, avisos_vagas = tratar_vagas(df_vagas_bruto)
    vagas_ok = not df_vagas.empty
except Exception as e:
    df_vagas, vagas_incompletos, avisos_vagas = None, None, []
    st.sidebar.warning(f"Vagas: não foi possível ler ({e})")

with st.sidebar:
    st.divider()
    if pilares_ok or vagas_ok:
        pdf_bytes = gerar_pdf(
            df_pilares=df_pilares, avisos_pilares=avisos_pilares,
            df_vagas=df_vagas, avisos_vagas=avisos_vagas,
        )
        st.download_button(
            "📄 Gerar relatório em PDF",
            data=pdf_bytes,
            file_name="relatorio_obra.pdf",
            mime="application/pdf",
            width="stretch",
        )

if not pilares_ok and not vagas_ok:
    st.error("Não foi possível carregar nenhum dado válido desta planilha.")
    st.stop()

aba_pilares, aba_vagas = st.tabs([" Pilares", " Vagas de Estacionamento"])

with aba_pilares:
    if pilares_ok:
        dashboard.mostrar_indicadores(df_pilares)
        dashboard.mostrar_avisos(avisos_pilares, pilares_incompletos)

        st.write("")
        col_esq, col_dir = st.columns([1.3, 1])
        with col_esq:
            st.markdown("#### Área por pilar")
            dashboard.grafico_area_por_pilar(df_pilares)
        with col_dir:
            st.markdown("#### Pilares por setor")
            dashboard.grafico_pizza_setor(df_pilares)

        st.markdown("#### Distribuição das áreas")
        dashboard.grafico_histograma(df_pilares)

        st.markdown("#### Tabela de pilares")
        dashboard.tabela_filtravel(df_pilares)

        st.write("")
        dashboard.botao_relatorio(df_pilares, pilares_incompletos, avisos_pilares)
    else:
        st.info("Nenhum pilar com dados completos foi encontrado nesta planilha.")

with aba_vagas:
    if vagas_ok:
        ind_vagas = dashboard_vagas.mostrar_indicadores_vagas(df_vagas)
        dashboard_vagas.mostrar_avisos_vagas(avisos_vagas, vagas_incompletos)

        st.write("")
        col_esq, col_dir = st.columns([1, 1])
        with col_esq:
            st.markdown("#### Real vs. projeto (Base x Altura)")
            dashboard_vagas.grafico_dispersao_real_vs_projeto(df_vagas, ind_vagas)
        with col_dir:
            st.markdown("#### Distribuição do desvio de área")
            dashboard_vagas.grafico_distribuicao_desvio(df_vagas)

        st.markdown("#### Desvio de área por vaga vs. projeto")
        dashboard_vagas.grafico_desvio_por_vaga(df_vagas)

        st.markdown("#### Tabela de conformidade")
        dashboard_vagas.tabela_vagas(df_vagas)
    else:
        st.info("Nenhuma vaga com dados completos foi encontrada nesta planilha.")
