# ╔══════════════════════════════════════════════════════════════════════╗
# ║  CCET • Base 1 — Dashboard Interativo (Streamlit)                    ║
# ║  Autor: Victor Hugo da Costa Fernandes (UFSCar — Eng. Produção)      ║
# ║  Orientador: Prof. Fábio Molina                                       ║
# ╠══════════════════════════════════════════════════════════════════════╣
# ║  Sobre                                                               ║
# ║  • Lê um arquivo Excel (.xlsx) enviado pelo usuário (sem CSVs).      ║
# ║  • Cria a coluna Tempo_Curso = Ano Egresso − Ingresso-Ano.           ║
# ║  • Filtros-mestre: Campus e Tipo de Ingresso.                         ║
# ║  • Páginas:                                                           ║
# ║      1) Qtde por curso por ano (1 curso)                              ║
# ║      2) Qtde por curso por ano (todos — cores + legenda + hover)      ║
# ║      3) Modalidades SISU por ano (1+ cursos)                          ║
# ║      4) Comparar 1 modalidade SISU entre cursos                       ║
# ║      5) Todos os Status (1 curso)                                     ║
# ║      6) Comparar 1 Status entre cursos                                ║
# ║      7) Tempo ingresso–egresso (comparação entre cursos)              ║
# ║      8) Análise de Cancelamentos                                      ║
# ║      9) Informações & Créditos                                        ║
# ╠══════════════════════════════════════════════════════════════════════╣
# ║  Origem dos Dados                                                    ║
# ║  • Base oficial da UFSCar — período considerado: até 2025.           ║
# ║  • Atualização não automática (snapshot).                             ║
# ╠══════════════════════════════════════════════════════════════════════╣
# ║  Objetivo                                                            ║
# ║  • Contextualizar o CCET: volumes, modalidades de ingresso,          ║
# ║    status acadêmicos e tempo de formação.                            ║
# ╠══════════════════════════════════════════════════════════════════════╣
# ║  Contato                                                             ║
# ║  • GitHub:   https://github.com/vhdacosta/                           ║
# ║  • LinkedIn: https://linkedin.com/in/vhdacosta/                      ║
# ╚══════════════════════════════════════════════════════════════════════╝
# ▶ Execução local:  streamlit run app_ccet_base1.py

import pandas as pd
import numpy as np
import altair as alt
import streamlit as st
from pathlib import Path
# ========== CONFIG ==========
st.set_page_config(page_title="CCET • Base 1", layout="wide")

NEEDED_COLS = [
    "Curso", "Campus", "centro", "turno", "Status", "Ingresso",
    "Ingresso-Ano", "Ano Egresso", "Modalidade SISU", "Descrição Modalidade SISU"
]

# ========== PREPROCESSING & FILTERS ==========

def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    # Garante presença das colunas
    missing = [c for c in NEEDED_COLS if c not in df.columns]
    if missing:
        st.error(f"Colunas ausentes no Excel: {missing}")
        st.stop()

    # ➜ **Whitelist**: mantém só o necessário
    df = df[NEEDED_COLS].copy()

    # Texto
    text_cols = ["Curso", "Campus", "centro", "turno", "Status", "Ingresso", "Descrição Modalidade SISU"]
    for col in text_cols:
        df[col] = df[col].astype("string").str.strip()

    df["centro"] = df["centro"].str.upper()

    # SISU
    df["Modalidade SISU"] = pd.to_numeric(df["Modalidade SISU"], errors="coerce").fillna(0).astype(int)
    df["Descrição Modalidade SISU"] = (
        df["Descrição Modalidade SISU"].fillna("").replace("(null)", "").str.strip()
    )

    # Anos
    df["Ingresso-Ano"] = pd.to_numeric(df["Ingresso-Ano"], errors="coerce")
    df["Ano Egresso"]  = pd.to_numeric(df["Ano Egresso"],  errors="coerce")

    # Tempo
    df["Tempo_Curso"] = df["Ano Egresso"] - df["Ingresso-Ano"]
    df.loc[(df["Tempo_Curso"] < 0) | (df["Tempo_Curso"] > 20), "Tempo_Curso"] = np.nan

    # Foco CCET (regex desativado)
    mask_ccet = df["centro"].str.contains("CCET", na=False, regex=False)
    df = df.loc[mask_ccet].copy()

    return df

def apply_master_filters(df: pd.DataFrame):
    st.sidebar.markdown("### Filtros-mestre")

    campus_opts = ["Todos"] + sorted(df["Campus"].dropna().unique().tolist())

    # tenta achar "São Carlos" de forma case-insensitive
    default_idx = 0
    for i, c in enumerate(campus_opts):
        if "SÃO CARLOS" in str(c).upper():
            default_idx = i
            break

    campus_sel = st.sidebar.selectbox("Campus", campus_opts, index=default_idx)

    ingresso_opts = ["Todos"] + sorted(df["Ingresso"].dropna().unique().tolist())
    ingresso_sel  = st.sidebar.selectbox("Tipo de Ingresso", ingresso_opts, index=0)

    f = df.copy()
    if campus_sel != "Todos":
        f = f[f["Campus"] == campus_sel]
    if ingresso_sel != "Todos":
        f = f[f["Ingresso"] == ingresso_sel]

    anos_validos = sorted([int(x) for x in f["Ingresso-Ano"].dropna().unique()])
    if anos_validos:
        min_ano, max_ano = min(anos_validos), max(anos_validos)
        ano_ini, ano_fim = st.sidebar.slider(
            "Intervalo de Anos de Ingresso",
            min_value=min_ano, max_value=max_ano,
            value=(min_ano, max_ano), step=1
        )
        f = f[(f["Ingresso-Ano"] >= ano_ini) & (f["Ingresso-Ano"] <= ano_fim)]

    # Hard cap para tabelas grandes (evita renderizar milhões de linhas por engano)
    if len(f) > 500_000:
        st.warning("Filtro resultou em mais de 500 mil linhas; refine os filtros.")
        f = f.sample(500_000, random_state=42)

    st.sidebar.info(f"{len(f):,} registros após filtros", icon="ℹ️")
    return f, campus_sel, ingresso_sel


# ========== HELPERS ==========

def cursos_sorted_with_ep_first(cursos: list[str]) -> list[str]:
    """Ordena cursos deixando Eng. Produção primeiro (se existir)."""
    return sorted(cursos, key=lambda x: (0 if "PRODU" in x.upper() else 1, x))

def get_default_courses(df_filtrado: pd.DataFrame, cursos_ordenados: list[str]) -> list[str]:
    """Top 3 por volume + Eng. de Produção + variações pré-2005 (se existirem)."""
    top3 = (
        df_filtrado.groupby("Curso")
        .size().sort_values(ascending=False).head(3).index.tolist()
    )

    ep_variants = [c for c in cursos_ordenados if "ENGENHARIA DE PRODUÇÃO" in c.upper()]
    # variações antigas (ajuste as regras se quiser mais refinado)
    pre2005_variants = [c for c in cursos_ordenados if "ENGENHARIA DE PRODUÇÃO -" in c.upper()]

    # combina preservando ordem e removendo duplicados
    combined = list(dict.fromkeys(top3 + ep_variants + pre2005_variants))
    return combined if combined else cursos_ordenados[:4]

def group_count(df: pd.DataFrame, by_cols: list[str], name="qtde") -> pd.DataFrame:
    return df.groupby(by_cols).size().reset_index(name=name)

def rolling_mean(df: pd.DataFrame, by_col: str, val_col: str, win: int) -> pd.DataFrame:
    """Aplica média móvel por curso no eixo temporal (Ingresso-Ano)."""
    if win <= 1:
        return df
    df = df.sort_values(["Curso", by_col]).copy()
    df[val_col] = df.groupby("Curso")[val_col].transform(lambda s: s.rolling(win, min_periods=1).mean())
    return df

def legend_modalidades_sisu(df_base: pd.DataFrame):
    st.markdown("---")
    st.subheader("Legenda • Modalidades do SISU")
    tab = (
        df_base[["Modalidade SISU", "Descrição Modalidade SISU"]]
        .drop_duplicates()
        .sort_values("Modalidade SISU")
        .reset_index(drop=True)
    )
    st.table(tab)

# SIDEBAR — upload de arquivo
# ========== LOAD & PREP (via upload) ==========

st.sidebar.header("Fonte de dados")
uploaded = st.sidebar.file_uploader("Envie o Excel (.xlsx) da Base 1", type=["xlsx"])

# Limite de tamanho (ex.: 30 MB). Ajuste se precisar.
MAX_MB = 30
if uploaded is not None and uploaded.size > MAX_MB * 1024 * 1024:
    st.error(f"Arquivo muito grande (> {MAX_MB} MB). Envie um .xlsx menor.")
    st.stop()

# Botão para limpar cache manualmente
if st.sidebar.button("🧹 Limpar cache de dados"):
    st.cache_data.clear()
    st.sidebar.success("Cache limpo.")

@st.cache_data(ttl=0, max_entries=3, show_spinner=True)
def load_data_from_upload(file) -> pd.DataFrame:
    # engine explícito evita fallback inesperado
    df = pd.read_excel(file, engine="openpyxl")
    return df.copy()

if uploaded is None:
    st.info(
        "Envie a planilha **.xlsx** para começar.\n\n"
        "• O arquivo é usado **apenas na sua sessão** e não é salvo no servidor.\n"
        "• Após o upload, todas as páginas e filtros ficam disponíveis.",
        icon="📄"
    )
    st.stop()


# ========== APP BODY ==========

# carrega & pré-processa
raw = load_data_from_upload(uploaded)

df = preprocess(raw)
f, campus_sel, ingresso_sel = apply_master_filters(df)

# navegação
pages = [
    "Qtde por curso por ano (1 curso)",
    "Qtde por curso por ano (todos, cores + legenda + hover)",
    "Modalidades SISU por ano (filtrando 1+ cursos)",
    "Comparar 1 Modalidade SISU entre cursos",
    "Todos os Status (1 curso)",
    "Comparar 1 Status entre cursos",
    "Tempo ingresso–egresso (todos cursos)",
    "Análise de Cancelamentos",
    "Informações & Créditos"
]
page = st.sidebar.radio("Páginas", pages, index=0)

# lista de cursos
cursos = cursos_sorted_with_ep_first(sorted(f["Curso"].dropna().unique()))
default_courses = get_default_courses(f, cursos)

# --------------------------
# 1) Curso único — séries anuais
# --------------------------
if page == pages[0]:
    st.title("Quantidade por Curso por Ano (Curso Único)")

    curso_sel = st.selectbox("Escolha o curso", options=cursos)
    g = group_count(f[f["Curso"] == curso_sel], ["Ingresso-Ano", "Curso"])

    colA, colB = st.columns([2, 1])
    with colA:
        st.dataframe(g, use_container_width=True)
    with colB:
        st.metric("Registros", f"{len(g):,}")
        st.metric("Período", f"{int(g['Ingresso-Ano'].min())}–{int(g['Ingresso-Ano'].max())}")

    chart = (
        alt.Chart(g)
        .mark_line(point=True)
        .encode(
            x=alt.X("Ingresso-Ano:O", title="Ano de Ingresso"),
            y=alt.Y("qtde:Q", title="Quantidade"),
            tooltip=["Ingresso-Ano", "qtde"]
        )
        .properties(height=420)
    )
    st.altair_chart(chart, use_container_width=True)

# --------------------------
# 2) Todos os cursos — cores + legenda + hover + média móvel
# --------------------------
elif page == pages[1]:
    st.title("Quantidade por Curso por Ano (Todos os Cursos)")

    with st.expander("Opções de exibição", expanded=True):
        cursos_mult = st.multiselect(
            "Cursos exibidos",
            options=cursos,
            default=default_courses
        )
        win = st.slider("Média móvel (janelas em anos)", min_value=1, max_value=7, value=1, step=1)

    df_sel = f[f["Curso"].isin(cursos_mult)] if cursos_mult else f.copy()
    g = group_count(df_sel, ["Ingresso-Ano", "Curso"])
    g_smooth = rolling_mean(g, by_col="Ingresso-Ano", val_col="qtde", win=win)

    # Cores estáveis pela ordem selecionada (ou todos)
    domain_cursos = cursos_mult if cursos_mult else cursos
    color_enc = alt.Color(
        "Curso:N",
        title="Curso",
        scale=alt.Scale(scheme="tableau20", domain=domain_cursos),
        legend=alt.Legend(orient="right")
    )

    # DUAS seleções: 1) hover em pontos  2) interação pela legenda
    hover_pts = alt.selection_point(fields=["Curso"], on="mouseover", nearest=True, empty=False)
    legend_sel = alt.selection_point(fields=["Curso"], bind="legend")

    # Camada de linhas
    lines = (
        alt.Chart(g_smooth)
        .mark_line(strokeWidth=2)
        .encode(
            x=alt.X("Ingresso-Ano:Q", title="Ano de Ingresso", axis=alt.Axis(format="d")),
            y=alt.Y("qtde:Q", title="Quantidade de Discentes"),
            color=color_enc,
            opacity=alt.condition(legend_sel | hover_pts, alt.value(1), alt.value(0.25)),
            tooltip=[
                alt.Tooltip("Curso:N", title="Curso"),
                alt.Tooltip("Ingresso-Ano:Q", title="Ano", format="d"),
                alt.Tooltip("qtde:Q", title="Qtde")
            ],
        )
        .properties(height=520, width="container")
    )

    # Pontos invisíveis só para capturar hover (melhora muito a interação)
    points_invis = (
        alt.Chart(g_smooth)
        .mark_point(opacity=0, size=100)
        .encode(
            x="Ingresso-Ano:Q",
            y="qtde:Q",
            color="Curso:N"
        )
        .add_params(hover_pts)
    )

    chart = (lines.add_params(legend_sel) + points_invis).interactive()

    st.altair_chart(chart, use_container_width=True)

    # Métricas rápidas
    tot = g.groupby("Curso")["qtde"].sum().sort_values(ascending=False)
    st.caption(
        "Top por volume (filtro atual): " +
        ", ".join([f"{c} ({int(t)})" for c, t in tot.head(5).items()])
    )

# --------------------------
# 3) Modalidades SISU por ano (1+ cursos)
# --------------------------
elif page == pages[2]:
    st.title("Modalidades SISU por Ano (Filtrar 1+ Cursos)")
    cursos_mult = st.multiselect("Escolha 1+ cursos", options=cursos,
                                 default=default_courses[:3] if len(default_courses) >= 3 else cursos)
    df_sel = f[f["Curso"].isin(cursos_mult)] if cursos_mult else f.copy()

    g = group_count(df_sel, ["Ingresso-Ano", "Modalidade SISU"])
    chart = (
        alt.Chart(g).mark_line(point=True)
        .encode(
            x=alt.X("Ingresso-Ano:O", title="Ano"),
            y=alt.Y("qtde:Q", title="Quantidade"),
            color=alt.Color("Modalidade SISU:N", title="Modalidade"),
            tooltip=["Ingresso-Ano", "Modalidade SISU", "qtde"]
        ).properties(height=460)
    )
    st.altair_chart(chart, use_container_width=True)
    legend_modalidades_sisu(df)

# --------------------------
# 4) Comparar 1 Modalidade SISU entre cursos
# --------------------------
elif page == pages[3]:
    st.title("Comparar 1 Modalidade SISU entre Cursos")
    modalidade_opts = sorted(f["Modalidade SISU"].dropna().unique())
    modalidade_sel = st.selectbox("Modalidade SISU", options=modalidade_opts)

    modo = st.radio("Modo", ["Total por curso", "Por ano"], horizontal=True)
    df_mod = f[f["Modalidade SISU"] == modalidade_sel].copy()

    if modo == "Total por curso":
        g = group_count(df_mod, ["Curso"]).sort_values("qtde", ascending=False)
        chart = (
            alt.Chart(g).mark_bar()
            .encode(
                x=alt.X("qtde:Q", title="Quantidade"),
                y=alt.Y("Curso:N", sort="-x", title="Curso"),
                tooltip=["Curso", "qtde"]
            ).properties(height=520)
        )
    else:
        g = group_count(df_mod, ["Ingresso-Ano", "Curso"])
        chart = (
            alt.Chart(g).mark_line(point=True)
            .encode(
                x=alt.X("Ingresso-Ano:O", title="Ano"),
                y=alt.Y("qtde:Q", title="Quantidade"),
                color=alt.Color("Curso:N", legend=None),
                tooltip=["Curso", "Ingresso-Ano", "qtde"]
            ).properties(height=520)
        )

    st.altair_chart(chart, use_container_width=True)
    legend_modalidades_sisu(df)

# --------------------------
# 5) Todos os Status por curso (curso único)
# --------------------------
elif page == pages[4]:
    st.title("Todos os Status por Curso (Curso Único)")
    curso_sel = st.selectbox("Escolha o curso", options=cursos)
    g = group_count(f[f["Curso"] == curso_sel], ["Status"]).sort_values("qtde", ascending=False)

    colA, colB = st.columns([2, 1])
    with colA:
        chart = (
            alt.Chart(g).mark_bar()
            .encode(
                x=alt.X("qtde:Q", title="Quantidade"),
                y=alt.Y("Status:N", sort="-x", title="Status"),
                tooltip=["Status", "qtde"]
            ).properties(height=520)
        )
        st.altair_chart(chart, use_container_width=True)
    with colB:
        st.dataframe(g, use_container_width=True)

# --------------------------
# 6) Comparar 1 Status entre cursos
# --------------------------
elif page == pages[5]:
    st.title("Comparar 1 Status entre Cursos")
    status_opts = sorted(f["Status"].dropna().unique())
    status_sel = st.selectbox("Status", options=status_opts)

    modo = st.radio("Modo", ["Total por curso", "Por ano"], horizontal=True)
    df_stat = f[f["Status"] == status_sel].copy()

    if modo == "Total por curso":
        g = group_count(df_stat, ["Curso"]).sort_values("qtde", ascending=False)
        chart = (
            alt.Chart(g).mark_bar()
            .encode(
                x=alt.X("qtde:Q", title="Quantidade"),
                y=alt.Y("Curso:N", sort="-x", title="Curso"),
                tooltip=["Curso", "qtde"]
            ).properties(height=520)
        )
    else:
        g = group_count(df_stat, ["Ingresso-Ano", "Curso"])
        chart = (
            alt.Chart(g).mark_line(point=True)
            .encode(
                x=alt.X("Ingresso-Ano:O", title="Ano"),
                y=alt.Y("qtde:Q", title="Quantidade"),
                color=alt.Color("Curso:N", legend=None),
                tooltip=["Curso", "Ingresso-Ano", "qtde"]
            ).properties(height=520)
        )

    st.altair_chart(chart, use_container_width=True)
# --------------------------
# 7) Tempo entre ingresso–egresso (todos cursos) — com filtro de Status
# --------------------------
elif page == pages[6]:
    st.title("Tempo entre Ingresso–Egresso (Comparação entre Cursos)")

    col_ctrl1, col_ctrl2 = st.columns([1,1])
    with col_ctrl1:
        cursos_mult = st.multiselect(
            "Escolha 1+ cursos",
            options=cursos,
            default=default_courses[:3] if len(default_courses) >= 3 else cursos
        )
    with col_ctrl2:
        status_opts = sorted(f["Status"].dropna().unique())
        # deixe vazio = todos; se preferir um default específico, mude aqui
        status_mult = st.multiselect(
            "Filtrar Status (1+ opcional)",
            options=status_opts,
            default=[]
        )

    df_sel = f[f["Curso"].isin(cursos_mult)] if cursos_mult else f.copy()
    if status_mult:  # aplica filtro só se houver seleção
        df_sel = df_sel[df_sel["Status"].isin(status_mult)]

    # tira NaNs/valores inválidos de tempo
    t = df_sel.dropna(subset=["Tempo_Curso"]).copy()
    t = t[(t["Tempo_Curso"] >= 0) & (t["Tempo_Curso"] <= 20)]

    st.caption(
        f"Registros com Tempo_Curso válido: {len(t):,}. "
        "Filtros aplicados acima. Valores negativos ou > 20 anos foram descartados."
    )

    # modos de comparação
    modo = st.radio("Modo de comparação", ["Boxplot", "Pontos (strip)"], horizontal=True)
    layout = st.radio("Disposição", ["Agrupar (cores por Status)", "Facetas por Status"], horizontal=True)

    # ajuda a reduzir ruído visual
    show_legend = st.checkbox("Mostrar legenda de Status", value=True)

    # Agrupar: um gráfico só, cores por status
    if layout == "Agrupar (cores por Status)":
        color_enc = alt.Color(
            "Status:N",
            title="Status",
            legend=alt.Legend(orient="right") if show_legend else None
        )

        if modo == "Boxplot":
            chart = (
                alt.Chart(t)
                .mark_boxplot(extent="min-max")
                .encode(
                    x=alt.X("Curso:N", sort="-y", title="Curso"),
                    y=alt.Y("Tempo_Curso:Q", title="Tempo (anos)"),
                    color=color_enc,
                    tooltip=["Curso", "Status", "Tempo_Curso"]
                )
                .properties(height=520)
            )
        else:
            # downsample p/ performance
            t_plot = t.sample(min(len(t), 20000), random_state=42)
            chart = (
                alt.Chart(t_plot)
                .mark_circle(size=35, opacity=0.35)
                .encode(
                    x=alt.X("Curso:N", sort="-y", title="Curso"),
                    y=alt.Y("Tempo_Curso:Q", title="Tempo (anos)"),
                    color=color_enc,
                    tooltip=["Curso", "Status", "Ingresso-Ano", "Ano Egresso", "Tempo_Curso"]
                )
                .properties(height=520)
            )

    # Facetas: um painel por status (bom quando escolhe 1–3 status)
    else:
        n_cols = st.slider("Nº de colunas nas facetas", 1, 4, 3)
        if modo == "Boxplot":
            base = alt.Chart(t).mark_boxplot(extent="min-max")
        else:
            t_plot = t.sample(min(len(t), 20000), random_state=42)
            base = alt.Chart(t_plot).mark_circle(size=35, opacity=0.35)

        chart = (
            base.encode(
                x=alt.X("Curso:N", sort="-y", title="Curso"),
                y=alt.Y("Tempo_Curso:Q", title="Tempo (anos)"),
                color=alt.Color("Curso:N", legend=None) if modo != "Boxplot" else alt.value("#4c78a8"),
                column=alt.Column("Status:N", title=None, header=alt.Header(labelOrient="bottom")),
                tooltip=["Curso", "Status", "Tempo_Curso"]
            )
            .resolve_scale(y="shared")  # mesma escala de Y entre facetas
            .properties(height=420)
        ).configure_facet(columns=n_cols)

    st.altair_chart(chart, use_container_width=True)

    # resumo estatístico útil para o TCC
    with st.expander("Resumo estatístico (Tempo_Curso)", expanded=False):
        resumo = (
            t.groupby(["Curso", "Status"])["Tempo_Curso"]
            .agg(qtd="count", media="mean", mediana="median", desvio="std", p25=lambda s: s.quantile(0.25), p75=lambda s: s.quantile(0.75))
            .reset_index()
            .sort_values(["Curso", "Status"])
        )
        st.dataframe(resumo, use_container_width=True)


# --------------------------
# 8) Análise de Cancelamentos
# --------------------------
elif page == "Análise de Cancelamentos":
    st.title("🔍 Análise de Cancelamentos (Entendendo o Pico 2007–2009)")

    # filtro opcional: anos alvo
    anos_focus = st.slider(
        "Selecione o intervalo de Anos de Ingresso para análise",
        int(f["Ingresso-Ano"].min()), int(f["Ingresso-Ano"].max()),
        (2005, 2011), step=1
    )

    f_focus = f[(f["Ingresso-Ano"] >= anos_focus[0]) & (f["Ingresso-Ano"] <= anos_focus[1])].copy()

    # 1️⃣ % Cancelados por Curso e Ano
    g_status = (
        f_focus.groupby(["Ingresso-Ano", "Curso", "Status"])
        .size().reset_index(name="qtde")
    )
    total_ano_curso = g_status.groupby(["Ingresso-Ano", "Curso"])["qtde"].sum().reset_index(name="total")
    cancelados = g_status[g_status["Status"].str.upper().str.contains("CANCEL", na=False)]
    cancelados = cancelados.merge(total_ano_curso, on=["Ingresso-Ano", "Curso"], how="left")
    cancelados["pct_cancel"] = (cancelados["qtde"] / cancelados["total"]) * 100

    chart1 = (
        alt.Chart(cancelados)
        .mark_line(point=True)
        .encode(
            x=alt.X("Ingresso-Ano:O", title="Ano de Ingresso"),
            y=alt.Y("pct_cancel:Q", title="% de Cancelados"),
            color=alt.Color("Curso:N", title="Curso", scale=alt.Scale(scheme="tableau20")),
            tooltip=["Curso", "Ingresso-Ano", alt.Tooltip("pct_cancel:Q", title="% Cancelados", format=".1f")]
        )
        .properties(height=420)
        .interactive()
    )
    st.subheader("1️⃣ Evolução percentual de cancelamentos por curso")
    st.altair_chart(chart1, use_container_width=True)
    st.caption("Obs.: pico anômalo em 2007–2009 pode indicar mudança de política de matrícula, evasão ou reestruturação curricular.")

    # 2️⃣ Cancelamentos por tipo de ingresso
    g_ingresso = (
        f_focus[f_focus["Status"].str.upper().str.contains("CANCEL", na=False)]
        .groupby(["Ingresso-Ano", "Ingresso"])
        .size().reset_index(name="qtde")
    )

    chart2 = (
        alt.Chart(g_ingresso)
        .mark_bar()
        .encode(
            x=alt.X("Ingresso-Ano:O", title="Ano de Ingresso"),
            y=alt.Y("qtde:Q", title="Qtde Cancelados"),
            color=alt.Color("Ingresso:N", title="Tipo de Ingresso"),
            tooltip=["Ingresso-Ano", "Ingresso", "qtde"]
        )
        .properties(height=420)
    )
    st.subheader("2️⃣ Cancelamentos por Tipo de Ingresso")
    st.altair_chart(chart2, use_container_width=True)

    # 3️⃣ Cancelamentos por Modalidade SISU (se existir)
    if f_focus["Modalidade SISU"].nunique() > 1:
        g_sisu = (
            f_focus[f_focus["Status"].str.upper().str.contains("CANCEL", na=False)]
            .groupby(["Ingresso-Ano", "Modalidade SISU"])
            .size().reset_index(name="qtde")
        )

        chart3 = (
            alt.Chart(g_sisu)
            .mark_line(point=True)
            .encode(
                x=alt.X("Ingresso-Ano:O", title="Ano de Ingresso"),
                y=alt.Y("qtde:Q", title="Qtde Cancelados"),
                color=alt.Color("Modalidade SISU:N", title="Modalidade SISU"),
                tooltip=["Ingresso-Ano", "Modalidade SISU", "qtde"]
            )
            .properties(height=400)
        )
        st.subheader("3️⃣ Cancelamentos por Modalidade SISU")
        st.altair_chart(chart3, use_container_width=True)
    
    legend_modalidades_sisu(df)

# --------------------------
# 9) Informações & Créditos
# --------------------------
elif page == pages[8]:
    st.title("ℹ️ Informações & Créditos")
    st.markdown("""
**Origem dos Dados**
- Base oficial da UFSCar  
- Período considerado: **até 2025**  
- Atualização **não automática** (snapshot)

**Objetivo**
- Contextualizar o CCET: volumes, modalidades de ingresso, status acadêmicos e tempo de formação.

**Autor**
- Victor Hugo da Costa Fernandes (UFSCar — Engenharia de Produção)

**Orientador**
- Prof. Fábio Molina

**Contato**
- GitHub: https://github.com/vhdacosta/
- LinkedIn: https://linkedin.com/in/vhdacosta/

---
Dashboard desenvolvido para fins de pesquisa acadêmica.
    """)

# --------------------------
# Rodapé
# --------------------------
st.markdown("---")
st.caption(
    "Base 1 — CCET • Filtros-mestre aplicados: "
    f"Campus = **{campus_sel}**, Ingresso = **{ingresso_sel}**. "
    "App pronto para versionar/deploy."
)
