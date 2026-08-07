# 🏗️ Dashboard de Pilares e Vagas — Ferramenta de Apoio à Inspeção Estrutural

Aplicação web que recebe uma planilha Excel com o levantamento de uma obra
(pilares e vagas de estacionamento) e devolve, automaticamente: tratamento
dos dados, cálculo de área, estatística (média/desvio padrão) comparando o
real com o projeto, indicadores, gráficos e um relatório em PDF.

Já entrega **v1 (Pilares)** e **v2 (Vagas de Estacionamento)** do roadmap.

## Como funciona

```text
Excel (upload ou data/pilares_V2.xlsx)
   │
   ├── aba 1 (pilares)  ──► tratamento.py        ──► dashboard.py
   │                         limpa/valida,             indicadores,
   │                         Área = Base × Largura     gráficos, tabela
   │
   └── aba "vagas..."   ──► tratamento_vagas.py  ──► dashboard_vagas.py
                             normaliza orientação,      indicadores,
                             compara real vs. projeto,  dispersão real vs.
                             média/desvio padrão        projeto, tabela

app.py (abas Pilares / Vagas) ──► relatorio_pdf.py ──► PDF para download
```

## Rodando localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

Abra o link que aparecer no terminal (por padrão `http://localhost:8501`).
Sem fazer upload de nada, a aplicação já sobe usando o exemplo em
`data/pilares.xlsx`.

## Estrutura do projeto

```text
pillar-dashboard/
│
├── data/
│   └── pilares_V2.xlsx    # planilha de exemplo (real, 2 abas)
│
├── app.py                 # interface Streamlit (ponto de entrada, abas)
├── tratamento.py          # limpeza/validação dos pilares + cálculo de área
├── dashboard.py           # indicadores, gráficos e tabela - pilares
├── tratamento_vagas.py    # limpeza/validação das vagas + real vs. projeto
├── dashboard_vagas.py     # indicadores, gráficos e tabela - vagas
├── relatorio_pdf.py       # relatório consolidado em PDF (reportlab + matplotlib)
├── requirements.txt
└── README.md
```

## O que a planilha de exemplo mostra

A planilha inclui 14 pilares do setor **SS2** com medidas completas e 9 linhas
do setor **SS1** só com o setor preenchido — simulando pilares que ainda não
foram medidos em campo. O `tratamento.py` separa essas linhas automaticamente
em vez de deixá-las quebrar os cálculos, e o dashboard mostra quantas ficaram
pendentes.

Colunas esperadas em qualquer planilha enviada:

| Coluna | Descrição |
| --- | --- |
| ID | Identificador único do pilar (ex.: P01) |
| Nome | Nome/apelido do pilar |
| Setor | Setor/subsolo/pavimento onde está o pilar |
| Base (cm) | Uma dimensão da seção transversal |
| Largura (cm) | Outra dimensão da seção transversal |

A coluna **Área (m²)** é sempre recalculada pelo próprio app
(`Área = (Base/100) × (Largura/100)`), nunca herdada direto da planilha — isso
evita indicadores errados se a planilha original vier com a fórmula quebrada.

## Indicadores e gráficos

**Pilares:** total de pilares, área total, área média, maior/menor pilar,
gráfico de barras (área por pilar), histograma, pizza por setor, tabela
filtrável, relatório resumido em `.md`.

**Vagas de estacionamento (real vs. projeto):** as duas dimensões de cada
vaga são normalizadas antes de comparar (a menor medida vira "Base", a
maior vira "Altura"), porque em campo a vaga pode ter sido medida em
qualquer orientação. A especificação de projeto (`Base = 250 cm`,
`Altura = 450 cm`, ajustável em `tratamento_vagas.py`) é comparada contra
cada vaga real, gerando:

- média e **desvio padrão** de Base e Altura reais;
- desvio (cm e %) de cada vaga vs. o projeto, com uma faixa de tolerância
  (padrão: 5%) que marca a vaga como dentro/fora do padrão;
- gráfico de dispersão Base × Altura real com o ponto do projeto marcado;
- gráfico de barras do desvio de área por vaga (verde = dentro, vermelho = fora);
- histograma da distribuição dos desvios;
- tabela de conformidade filtrável (por setor, ou só as fora do padrão).

## Relatório em PDF

O botão **"Gerar relatório em PDF"** na barra lateral consolida os dois
módulos num único PDF: indicadores, gráficos (renderizados com matplotlib,
sem depender de nenhum binário externo) e a tabela completa de conformidade
das vagas. Gerado on-demand com reportlab, sem etapa de exportação manual.

## Tecnologias

- Python
- Pandas + OpenPyXL (leitura e tratamento dos dados)
- Plotly (gráficos interativos no dashboard)
- Matplotlib + ReportLab (gráficos estáticos e montagem do PDF)
- Streamlit (interface/dashboard)

## Roadmap

```text
v1 → Pilares                              ✔
v2 → Vagas de estacionamento (real x projeto, com estatística)  ✔
v3 → Vigas
v4 → Lajes
v5 → Relatórios automáticos consolidados (todos os módulos)
```

Cada módulo novo entra como seu próprio par `tratamento_x.py` / `dashboard_x.py`
mais uma aba na barra lateral, sem precisar reescrever o que já existe.
