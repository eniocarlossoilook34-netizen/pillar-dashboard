"""
tratamento.py
--------------
Camada de tratamento de dados do dashboard de pilares.

Responsabilidades:
    - carregar a planilha (upload do usuário ou arquivo padrão em data/);
    - validar e limpar os dados (linhas incompletas, tipos, valores negativos);
    - calcular a área da seção transversal quando necessário;
    - gerar os indicadores usados no dashboard.

Nenhuma função aqui desenha nada na tela - isso fica a cargo do dashboard.py.
"""

from __future__ import annotations

import pandas as pd

REQUIRED_COLUMNS = ["ID", "Nome", "Setor", "Base (cm)", "Largura (cm)"]


def carregar_planilha(caminho_ou_buffer, sheet_name=0) -> pd.DataFrame:
    """Lê a planilha de pilares (aceita caminho em disco ou arquivo de upload).

    Por padrão lê a primeira aba do arquivo (sheet_name=0), pois a planilha
    de pilares pode vir com qualquer nome de aba (ex.: 'Página1').
    """
    df = pd.read_excel(caminho_ou_buffer, sheet_name=sheet_name)

    # normaliza nomes de coluna (remove espaços duplicados, etc.)
    df.columns = [str(c).strip() for c in df.columns]

    faltantes = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if faltantes:
        raise ValueError(
            "A planilha não tem as colunas esperadas: "
            + ", ".join(faltantes)
            + ". Colunas encontradas: "
            + ", ".join(df.columns)
        )
    return df


def tratar_dados(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    """
    Limpa e valida os dados.

    A planilha real de obra costuma trazer três tipos de linha misturados:
      1. pilares de fato, com Base e Largura preenchidas;
      2. pilares pendentes de levantamento (Setor já sabido, dimensões não);
      3. "ruído" de planilha de trabalho - linhas em branco deixadas de
         sobra, ou anotações do usuário digitadas numa célula qualquer
         (ex.: uma observação escrita na coluna ID). Nenhuma delas é um
         pilar, então não fazem sentido nem como "válida" nem como
         "pendente" - são apenas ignoradas, com aviso.

    Retorna:
        df_validos      -> pilares com Base/Largura numéricas e > 0, com a
                            coluna 'Área (m²)' recalculada em m². O ID não é
                            mais obrigatório: se faltar, um ID temporário é
                            gerado (ver comentário abaixo) para não jogar
                            fora um pilar que já tem as duas medidas.
        df_incompletos  -> pilares com Setor definido mas Base/Largura
                            ausentes (aguardando levantamento em campo).
        avisos          -> lista de mensagens legíveis sobre o que foi
                            corrigido/descartado, para exibir no dashboard.
    """
    avisos: list[str] = []
    df = df.copy()

    for col in ["Base (cm)", "Largura (cm)"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    colunas_chave = ["ID", "Nome", "Setor", "Base (cm)", "Largura (cm)"]
    linha_vazia = df[colunas_chave].isna().all(axis=1)
    df = df[~linha_vazia].copy()  # linhas 100% em branco: descarta em silêncio

    sem_dimensoes = df["Base (cm)"].isna() | df["Largura (cm)"].isna()

    # "pendente de fato": já se sabe o setor, só falta medir.
    pendente = sem_dimensoes & df["Setor"].notna()
    # sem setor e sem dimensões, mas com algo escrito em ID/Nome: não é um
    # pilar, é anotação/observação numa célula (ex.: uma pergunta digitada
    # na coluna ID). Ignorado, mas avisado.
    anotacao = sem_dimensoes & df["Setor"].isna() & (df["ID"].notna() | df["Nome"].notna())

    df_incompletos = df[pendente].copy()
    df_anotacoes = df[anotacao].copy()
    df_validos = df[~sem_dimensoes].copy()

    if len(df_anotacoes):
        exemplos = ", ".join(
            str(v) for v in pd.concat([df_anotacoes["ID"], df_anotacoes["Nome"]]).dropna().head(3)
        )
        avisos.append(
            f"{len(df_anotacoes)} linha(s) sem Setor/Base/Largura foram ignoradas por "
            f"parecerem anotações digitadas na planilha, não pilares (ex.: \"{exemplos}\")."
        )

    if len(df_incompletos):
        setores = df_incompletos["Setor"].dropna().unique()
        setores_txt = ", ".join(map(str, setores))
        avisos.append(
            f"{len(df_incompletos)} pilar(es) com setor definido mas sem Base/Largura foram "
            f"separados como pendentes de levantamento (setor: {setores_txt}) e não entram "
            f"nos indicadores."
        )

    # valores <= 0 não fazem sentido para uma dimensão física
    invalidas = df_validos[(df_validos["Base (cm)"] <= 0) | (df_validos["Largura (cm)"] <= 0)]
    if len(invalidas):
        avisos.append(
            f"{len(invalidas)} pilar(es) com Base ou Largura <= 0 foram descartados: "
            + ", ".join(invalidas["ID"].astype(str))
        )
        df_validos = df_validos.drop(invalidas.index)

    # ID deixou de ser obrigatório: um pilar com as duas medidas é válido
    # mesmo sem ID/Nome na planilha - só recebe um identificador temporário
    # para poder aparecer nos gráficos e não ser confundido com outro.
    sem_id = df_validos["ID"].isna()
    if sem_id.any():
        df_validos.loc[sem_id, "ID"] = [f"SEM-ID-{i+1}" for i in range(sem_id.sum())]
        avisos.append(
            f"{int(sem_id.sum())} pilar(es) sem ID receberam um identificador temporário "
            f"(SEM-ID-n) - preencha o ID na planilha para um nome definitivo."
        )
    df_validos["Nome"] = df_validos["Nome"].fillna(df_validos["ID"])

    duplicados = df_validos[df_validos.duplicated(subset="ID", keep=False)]
    if len(duplicados):
        avisos.append(
            "ID(s) duplicado(s) na planilha: "
            + ", ".join(sorted(set(duplicados["ID"].astype(str))))
        )

    # área sempre recalculada a partir de Base/Largura, nunca herdada da planilha,
    # para garantir consistência mesmo se a coluna original vier errada.
    df_validos["Área (m²)"] = (df_validos["Base (cm)"] / 100) * (df_validos["Largura (cm)"] / 100)
    df_validos["Área (m²)"] = df_validos["Área (m²)"].round(5)

    if "Setor" in df_validos.columns:
        df_validos["Setor"] = df_validos["Setor"].fillna("Não informado")

    df_validos = df_validos.reset_index(drop=True)
    df_incompletos = df_incompletos.reset_index(drop=True)

    return df_validos, df_incompletos, avisos


def calcular_indicadores(df: pd.DataFrame) -> dict:
    """Indicadores usados nos cartões (KPIs) do topo do dashboard."""
    if df.empty:
        return {
            "total_pilares": 0,
            "area_total": 0.0,
            "area_media": 0.0,
            "maior_pilar": None,
            "menor_pilar": None,
            "qtd_setores": 0,
        }

    idx_max = df["Área (m²)"].idxmax()
    idx_min = df["Área (m²)"].idxmin()

    return {
        "total_pilares": int(len(df)),
        "area_total": float(df["Área (m²)"].sum()),
        "area_media": float(df["Área (m²)"].mean()),
        "maior_pilar": {
            "id": df.loc[idx_max, "ID"],
            "area": float(df.loc[idx_max, "Área (m²)"]),
        },
        "menor_pilar": {
            "id": df.loc[idx_min, "ID"],
            "area": float(df.loc[idx_min, "Área (m²)"]),
        },
        "qtd_setores": int(df["Setor"].nunique()),
    }


def gerar_relatorio_texto(df: pd.DataFrame, df_incompletos: pd.DataFrame, avisos: list[str]) -> str:
    """Monta um relatório resumido em texto/Markdown para download."""
    ind = calcular_indicadores(df)
    linhas = [
        "# Relatório de Inspeção Estrutural - Pilares",
        "",
        f"Total de pilares analisados: **{ind['total_pilares']}**",
        f"Área total da seção transversal: **{ind['area_total']:.3f} m²**",
        f"Área média por pilar: **{ind['area_media']:.4f} m²**",
    ]
    if ind["maior_pilar"]:
        linhas.append(
            f"Maior pilar: **{ind['maior_pilar']['id']}** ({ind['maior_pilar']['area']:.4f} m²)"
        )
        linhas.append(
            f"Menor pilar: **{ind['menor_pilar']['id']}** ({ind['menor_pilar']['area']:.4f} m²)"
        )
    linhas.append(f"Setores distintos: **{ind['qtd_setores']}**")
    linhas.append("")

    linhas.append("## Área por setor")
    if not df.empty:
        por_setor = df.groupby("Setor")["Área (m²)"].agg(["count", "sum", "mean"])
        for setor, row in por_setor.iterrows():
            linhas.append(
                f"- {setor}: {int(row['count'])} pilar(es), "
                f"área total {row['sum']:.3f} m², média {row['mean']:.4f} m²"
            )
    linhas.append("")

    if avisos:
        linhas.append("## Observações do tratamento de dados")
        for a in avisos:
            linhas.append(f"- {a}")
        linhas.append("")

    if not df_incompletos.empty:
        linhas.append("## Pilares pendentes de levantamento em campo")
        for _, r in df_incompletos.iterrows():
            linhas.append(f"- Setor {r.get('Setor', 'N/A')}: aguardando Base e Largura")

    return "\n".join(linhas)
