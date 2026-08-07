"""
tratamento_vagas.py
--------------------
Camada de tratamento de dados do módulo de Vagas de Estacionamento (v2).

Diferente dos pilares, aqui o interesse central é comparar a medida REAL
de cada vaga com a medida de PROJETO (a especificação de referência) e
entender o quanto a execução em campo se desviou do projeto - com
estatística (média, desvio padrão) aplicada sobre esse desvio.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

REQUIRED_COLUMNS = ["ID", "Nome", "Setor", "Base (cm)", "Largura (cm)"]

# Especificação de projeto (valores nominais). Podem ser ajustados na
# chamada de tratar_vagas() se o projeto usar outra referência.
BASE_PROJETO_CM = 250.0
ALTURA_PROJETO_CM = 450.0
TOLERANCIA_PCT = 5.0  # acima disso, a vaga é marcada como fora do padrão


def _encontrar_aba_vagas(caminho_ou_buffer) -> str:
    """Acha a aba de vagas mesmo com variação de espaços/maiúsculas no nome."""
    xls = pd.ExcelFile(caminho_ou_buffer)
    for nome in xls.sheet_names:
        if "vaga" in nome.strip().lower():
            return nome
    raise ValueError(
        "Não encontrei uma aba de vagas na planilha. Abas disponíveis: "
        + ", ".join(xls.sheet_names)
    )


def carregar_vagas(caminho_ou_buffer) -> pd.DataFrame:
    """Lê a aba de vagas de estacionamento da planilha."""
    aba = _encontrar_aba_vagas(caminho_ou_buffer)
    df = pd.read_excel(caminho_ou_buffer, sheet_name=aba)
    df.columns = [str(c).strip() for c in df.columns]

    faltantes = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if faltantes:
        raise ValueError(
            "A aba de vagas não tem as colunas esperadas: " + ", ".join(faltantes)
        )
    return df


def tratar_vagas(
    df: pd.DataFrame,
    base_projeto: float = BASE_PROJETO_CM,
    altura_projeto: float = ALTURA_PROJETO_CM,
    tolerancia_pct: float = TOLERANCIA_PCT,
) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    """
    Limpa os dados e calcula o desvio de cada vaga em relação ao projeto.

    Como a vaga pode ter sido medida em qualquer orientação (a dimensão
    maior nem sempre cai na coluna 'Base'), as duas medidas de cada linha
    são normalizadas antes de comparar com o projeto:
        - a menor das duas   -> comparada à Base de projeto
        - a maior das duas   -> comparada à Altura de projeto

    Retorna:
        df_validos      -> uma linha por vaga, com medidas normalizadas,
                            desvio em cm e em %, e a flag 'Dentro do padrão'.
        df_incompletos  -> linhas sem Base/Largura numéricas.
        avisos          -> mensagens sobre o que foi corrigido/descartado.
    """
    avisos: list[str] = []
    df = df.copy()

    for col in ["Base (cm)", "Largura (cm)"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    colunas_chave = ["ID", "Nome", "Setor", "Base (cm)", "Largura (cm)"]
    linha_vazia = df[colunas_chave].isna().all(axis=1)
    df = df[~linha_vazia].copy()

    sem_dimensoes = df["Base (cm)"].isna() | df["Largura (cm)"].isna()
    df_incompletos = df[sem_dimensoes].copy().reset_index(drop=True)
    df_validos = df[~sem_dimensoes].copy()

    if len(df_incompletos):
        avisos.append(
            f"{len(df_incompletos)} vaga(s) sem Base/Largura numéricas foram "
            "separadas e não entram nos indicadores."
        )

    invalidas = df_validos[(df_validos["Base (cm)"] <= 0) | (df_validos["Largura (cm)"] <= 0)]
    if len(invalidas):
        avisos.append(
            f"{len(invalidas)} vaga(s) com Base ou Largura <= 0 foram descartadas: "
            + ", ".join(invalidas["ID"].astype(str))
        )
        df_validos = df_validos.drop(invalidas.index)

    sem_id = df_validos["ID"].isna()
    if sem_id.any():
        df_validos.loc[sem_id, "ID"] = [f"SEM-ID-{i+1}" for i in range(sem_id.sum())]
        avisos.append(f"{int(sem_id.sum())} vaga(s) sem ID receberam identificador temporário.")
    df_validos["Nome"] = df_validos["Nome"].fillna(df_validos["ID"])
    if "Setor" in df_validos.columns:
        df_validos["Setor"] = df_validos["Setor"].fillna("Não informado")

    # normaliza orientação: menor medida = "base", maior medida = "altura"
    dim1 = df_validos["Base (cm)"]
    dim2 = df_validos["Largura (cm)"]
    df_validos["Base real (cm)"] = np.minimum(dim1, dim2)
    df_validos["Altura real (cm)"] = np.maximum(dim1, dim2)
    df_validos["Área real (m²)"] = (
        df_validos["Base real (cm)"] / 100 * df_validos["Altura real (cm)"] / 100
    ).round(5)

    df_validos["Base projeto (cm)"] = base_projeto
    df_validos["Altura projeto (cm)"] = altura_projeto
    area_projeto = round((base_projeto / 100) * (altura_projeto / 100), 5)
    df_validos["Área projeto (m²)"] = area_projeto

    df_validos["Desvio Base (cm)"] = (df_validos["Base real (cm)"] - base_projeto).round(2)
    df_validos["Desvio Altura (cm)"] = (df_validos["Altura real (cm)"] - altura_projeto).round(2)
    df_validos["Desvio Base (%)"] = (df_validos["Desvio Base (cm)"] / base_projeto * 100).round(2)
    df_validos["Desvio Altura (%)"] = (
        df_validos["Desvio Altura (cm)"] / altura_projeto * 100
    ).round(2)
    df_validos["Desvio Área (%)"] = (
        (df_validos["Área real (m²)"] - area_projeto) / area_projeto * 100
    ).round(2)

    df_validos["Dentro do padrão"] = (
        df_validos["Desvio Base (%)"].abs().le(tolerancia_pct)
        & df_validos["Desvio Altura (%)"].abs().le(tolerancia_pct)
    )

    fora = (~df_validos["Dentro do padrão"]).sum()
    if fora:
        avisos.append(
            f"{int(fora)} de {len(df_validos)} vaga(s) fogem da especificação de projeto "
            f"(Base {base_projeto:.0f} cm × Altura {altura_projeto:.0f} cm) em mais de "
            f"{tolerancia_pct:.0f}%."
        )

    df_validos = df_validos.reset_index(drop=True)
    return df_validos, df_incompletos, avisos


def calcular_indicadores_vagas(df: pd.DataFrame, base_projeto=BASE_PROJETO_CM,
                                 altura_projeto=ALTURA_PROJETO_CM) -> dict:
    """Indicadores e estatística (média/desvio padrão) para os cartões e o relatório."""
    if df.empty:
        return {"total_vagas": 0}

    idx_max_desvio = df["Desvio Área (%)"].abs().idxmax()

    return {
        "total_vagas": int(len(df)),
        "area_total": float(df["Área real (m²)"].sum()),
        "area_media": float(df["Área real (m²)"].mean()),
        "base_media": float(df["Base real (cm)"].mean()),
        "base_desvio_padrao": float(df["Base real (cm)"].std(ddof=1)),
        "altura_media": float(df["Altura real (cm)"].mean()),
        "altura_desvio_padrao": float(df["Altura real (cm)"].std(ddof=1)),
        "desvio_base_pct_medio": float(df["Desvio Base (%)"].mean()),
        "desvio_altura_pct_medio": float(df["Desvio Altura (%)"].mean()),
        "qtd_dentro_padrao": int(df["Dentro do padrão"].sum()),
        "qtd_fora_padrao": int((~df["Dentro do padrão"]).sum()),
        "vaga_maior_desvio": {
            "id": df.loc[idx_max_desvio, "ID"],
            "desvio_pct": float(df.loc[idx_max_desvio, "Desvio Área (%)"]),
        },
        "base_projeto": base_projeto,
        "altura_projeto": altura_projeto,
    }
