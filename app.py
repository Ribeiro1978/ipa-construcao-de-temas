import streamlit as st
import pandas as pd
from datetime import date
from pathlib import Path
import json

st.set_page_config(
    page_title="IPA – Construção de Temas",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
DATA_FILE = DATA_DIR / "reunioes.json"
COMMISSIONS_FILE = DATA_DIR / "comissoes.json"

DEFAULT_COMISSOES = [
    "Alimentação e Saúde",
    "Ambiental",
    "Bioenergia",
    "Conselho Jurídico",
    "Defesa Animal",
    "Defesa Vegetal",
    "Direito de Propriedade",
    "Infraestrutura e Logística",
    "Política Agrícola",
    "Relações Internacionais",
    "Trabalhista",
    "Tributária",
]

DEFAULT_DATA = [
    {
        "id": 1,
        "data": "2026-09-22",
        "comissao": "Política Agrícola",
        "tema": "Seguro Rural",
        "assuntos_relacionados": ["PSR", "Crédito Rural"],
        "resumo": "Discussão sobre previsibilidade orçamentária do Seguro Rural e próximos passos após avanço legislativo.",
        "encaminhamentos": "Acompanhar regulamentação e consolidar pontos técnicos das entidades.",
        "comunicacao": "Sem demanda específica.",
        "status": "Em acompanhamento",
        "fonte": "Position Paper – reunião de 22/09/2026",
    },
    {
        "id": 2,
        "data": "2026-09-18",
        "comissao": "Defesa Vegetal",
        "tema": "Bioinsumos",
        "assuntos_relacionados": ["Regulamentação", "Uso próprio"],
        "resumo": "Entidades discutiram pontos da regulamentação da Lei 15.070/2024, com atenção ao uso próprio e registro.",
        "encaminhamentos": "Consolidar contribuições e acompanhar minuta de regulamentação.",
        "comunicacao": "Mapear mensagens para eventual material explicativo.",
        "status": "Em construção",
        "fonte": "Position Paper – reunião de 18/09/2026",
    },
    {
        "id": 3,
        "data": "2026-09-15",
        "comissao": "Política Agrícola",
        "tema": "Crédito Rural",
        "assuntos_relacionados": ["Plano Safra", "Endividamento"],
        "resumo": "Debate sobre acesso ao crédito, execução do Plano Safra e efeitos do endividamento sobre novos financiamentos.",
        "encaminhamentos": "Acompanhar dados de contratação e medidas de renegociação.",
        "comunicacao": "Preparar síntese se houver novo dado oficial.",
        "status": "Em acompanhamento",
        "fonte": "Position Paper – reunião de 15/09/2026",
    },
]


def load_comissoes():
    if not COMMISSIONS_FILE.exists():
        COMMISSIONS_FILE.write_text(json.dumps(DEFAULT_COMISSOES, ensure_ascii=False, indent=2), encoding="utf-8")
    return json.loads(COMMISSIONS_FILE.read_text(encoding="utf-8"))


def load_data():
    if not DATA_FILE.exists():
        save_data(DEFAULT_DATA)
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def save_data(data):
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def normalize(text):
    return str(text or "").lower().strip()


def matches(item, query):
    haystack = " ".join([
        item.get("tema", ""),
        item.get("comissao", ""),
        item.get("resumo", ""),
        item.get("encaminhamentos", ""),
        item.get("comunicacao", ""),
        item.get("status", ""),
        " ".join(item.get("assuntos_relacionados", [])),
    ])
    return normalize(query) in normalize(haystack)


def card(title, body, caption=None):
    st.markdown(
        f"""
        <div style="padding:18px;border:1px solid #E7E9EE;border-radius:16px;background:#FFFFFF;min-height:150px;">
            <div style="font-size:0.82rem;color:#657084;margin-bottom:8px;">{caption or ''}</div>
            <div style="font-size:1.15rem;font-weight:700;color:#172033;margin-bottom:8px;">{title}</div>
            <div style="font-size:0.95rem;color:#3E4758;line-height:1.45;">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


st.markdown(
    """
    <style>
    .block-container {padding-top: 1.6rem; padding-bottom: 3rem;}
    [data-testid="stSidebar"] {background-color: #F7F8FA;}
    h1, h2, h3 {color:#172033;}
    .muted {color:#687386;font-size:0.92rem;}
    .hero {
        padding: 28px 30px;
        border-radius: 22px;
        background: linear-gradient(135deg, #F5F7FA 0%, #FFFFFF 100%);
        border: 1px solid #E6E9EF;
        margin-bottom: 20px;
    }
    .hero h1 {font-size:2rem;margin-bottom:0.35rem;}
    .hero p {font-size:1rem;color:#667085;margin:0;}
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("## IPA")
    st.markdown("**Construção de Temas**")
    st.caption("Memória das comissões")
    st.divider()
    pagina = st.radio(
        "Navegação",
        ["Pesquisar", "Temas", "Comissões", "Reuniões", "Radar", "Adicionar position paper"],
        label_visibility="collapsed",
    )
    st.divider()
    st.caption("MVP 0.1 • Base local")

reunioes = load_data()
comissoes_oficiais = load_comissoes()

if pagina == "Pesquisar":
    st.markdown(
        """
        <div class="hero">
            <h1>IPA – Construção de Temas</h1>
            <p>Memória inteligente das discussões e encaminhamentos das comissões do IPA.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.subheader("Qual assunto você quer pesquisar hoje?")
    query = st.text_input(
        "Pesquisa",
        placeholder="Ex.: Seguro Rural, bioinsumos, crédito rural, regulamentação...",
        label_visibility="collapsed",
    )

    if query:
        resultados = [r for r in reunioes if matches(r, query)]
        if resultados:
            st.markdown(f"**{len(resultados)} registro(s) encontrado(s)**")
            for r in sorted(resultados, key=lambda x: x["data"], reverse=True):
                with st.container(border=True):
                    c1, c2, c3 = st.columns([2.2, 1.2, 1])
                    with c1:
                        st.markdown(f"### {r['tema']}")
                        st.write(r["resumo"])
                    with c2:
                        st.caption("Comissão")
                        st.write(r["comissao"])
                        st.caption("Data")
                        st.write(pd.to_datetime(r["data"]).strftime("%d/%m/%Y"))
                    with c3:
                        st.caption("Status")
                        st.write(r["status"])
                    st.markdown("**Encaminhamentos**")
                    st.write(r["encaminhamentos"])
                    st.markdown("**Comunicação**")
                    st.write(r["comunicacao"])
                    st.caption(r["fonte"])
        else:
            st.info("Nenhum registro encontrado para esse assunto.")
    else:
        st.markdown("#### Visão rápida")
        c1, c2, c3, c4 = st.columns(4)
        temas = sorted(set(r["tema"] for r in reunioes))
        comissoes = sorted(set(r["comissao"] for r in reunioes))
        com_demanda = [r for r in reunioes if "sem demanda" not in normalize(r["comunicacao"])]
        em_construcao = [r for r in reunioes if "construção" in normalize(r["status"])]
        c1.metric("Temas", len(temas))
        c2.metric("Comissões", len(comissoes))
        c3.metric("Demandas de Comunicação", len(com_demanda))
        c4.metric("Em construção", len(em_construcao))

        st.markdown("#### Últimos movimentos")
        ultimos = sorted(reunioes, key=lambda x: x["data"], reverse=True)[:3]
        cols = st.columns(3)
        for col, r in zip(cols, ultimos):
            with col:
                card(r["tema"], r["resumo"], f"{r['comissao']} • {pd.to_datetime(r['data']).strftime('%d/%m/%Y')}")

elif pagina == "Temas":
    st.title("Temas")
    st.caption("Acompanhe o histórico consolidado de cada assunto discutido no IPA.")

    temas = sorted(set(r["tema"] for r in reunioes))
    tema_escolhido = st.selectbox("Selecione um tema", temas)
    relacionados = [r for r in reunioes if r["tema"] == tema_escolhido]
    relacionados = sorted(relacionados, key=lambda x: x["data"])

    st.markdown(f"## {tema_escolhido}")
    st.write(relacionados[-1]["resumo"])

    c1, c2, c3 = st.columns(3)
    c1.metric("Reuniões relacionadas", len(relacionados))
    c2.metric("Comissões envolvidas", len(set(r["comissao"] for r in relacionados)))
    c3.metric("Último movimento", pd.to_datetime(relacionados[-1]["data"]).strftime("%d/%m/%Y"))

    st.markdown("### Linha do tempo")
    for r in relacionados:
        with st.container(border=True):
            st.markdown(f"**{pd.to_datetime(r['data']).strftime('%d/%m/%Y')} • {r['comissao']}**")
            st.write(r["resumo"])
            st.markdown(f"**Encaminhamento:** {r['encaminhamentos']}")
            st.caption(r["fonte"])

elif pagina == "Comissões":
    st.title("Comissões")
    st.caption("Estrutura fixa das comissões do IPA. Os temas e reuniões são vinculados a uma ou mais delas ao longo do tempo.")

    for nome in comissoes_oficiais:
        regs = [r for r in reunioes if r.get("comissao") == nome]
        temas = sorted(set(r.get("tema", "") for r in regs if r.get("tema")))
        with st.container(border=True):
            c1, c2, c3 = st.columns([2.5, 1, 1])
            with c1:
                st.markdown(f"### {nome}")
                if temas:
                    st.write(" • ".join(temas))
                else:
                    st.caption("Nenhum tema cadastrado ainda.")
            c2.metric("Temas", len(temas))
            c3.metric("Reuniões", len(regs))

elif pagina == "Reuniões":
    st.title("Reuniões")
    st.caption("Base completa dos registros acompanhados pela Comunicação.")

    df = pd.DataFrame(reunioes)
    if not df.empty:
        df["data"] = pd.to_datetime(df["data"]).dt.strftime("%d/%m/%Y")
        exibicao = df[["data", "comissao", "tema", "status", "encaminhamentos", "comunicacao"]]
        st.dataframe(exibicao, use_container_width=True, hide_index=True)

elif pagina == "Radar":
    st.title("Radar")
    st.caption("O que merece atenção nas comissões agora.")

    recentes = sorted(reunioes, key=lambda x: x["data"], reverse=True)
    demandas = [r for r in recentes if "sem demanda" not in normalize(r["comunicacao"])]
    construcao = [r for r in recentes if "construção" in normalize(r["status"])]

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### Temas em construção")
        if construcao:
            for r in construcao:
                with st.container(border=True):
                    st.markdown(f"**{r['tema']}**")
                    st.write(r["encaminhamentos"])
                    st.caption(f"{r['comissao']} • {pd.to_datetime(r['data']).strftime('%d/%m/%Y')}")
        else:
            st.info("Nenhum tema marcado como em construção.")

    with c2:
        st.markdown("### Demandas para Comunicação")
        if demandas:
            for r in demandas:
                with st.container(border=True):
                    st.markdown(f"**{r['tema']}**")
                    st.write(r["comunicacao"])
                    st.caption(f"{r['comissao']} • {pd.to_datetime(r['data']).strftime('%d/%m/%Y')}")
        else:
            st.info("Nenhuma demanda registrada.")

elif pagina == "Adicionar position paper":
    st.title("Adicionar position paper")
    st.caption("Nesta primeira versão, cadastramos os principais campos manualmente. A leitura automática por IA entra na próxima etapa.")

    with st.form("novo_registro"):
        col1, col2 = st.columns(2)
        with col1:
            data_reuniao = st.date_input("Data da reunião", value=date.today())
            comissao = st.text_input("Comissão", placeholder="Ex.: Política Agrícola")
            tema = st.text_input("Tema principal", placeholder="Ex.: Seguro Rural")
        with col2:
            status = st.selectbox("Status", ["Em construção", "Em acompanhamento", "Consolidado", "Aguardando retorno", "Encerrado"])
            relacionados = st.text_input("Assuntos relacionados", placeholder="Separe por vírgulas")
            fonte = st.text_input("Fonte", placeholder="Ex.: Position Paper – reunião de 29/09/2026")

        resumo = st.text_area("Resumo da discussão", height=140)
        encaminhamentos = st.text_area("Encaminhamentos", height=110)
        comunicacao = st.text_area("Demanda para Comunicação", height=90, value="Sem demanda específica.")
        arquivo = st.file_uploader("Anexar position paper (opcional nesta versão)", type=["pdf", "docx", "txt"])

        salvar = st.form_submit_button("Salvar registro", type="primary", use_container_width=True)

        if salvar:
            if not comissao or not tema or not resumo:
                st.error("Preencha pelo menos Comissão, Tema principal e Resumo da discussão.")
            else:
                novo = {
                    "id": max([r["id"] for r in reunioes], default=0) + 1,
                    "data": data_reuniao.isoformat(),
                    "comissao": comissao.strip(),
                    "tema": tema.strip(),
                    "assuntos_relacionados": [x.strip() for x in relacionados.split(",") if x.strip()],
                    "resumo": resumo.strip(),
                    "encaminhamentos": encaminhamentos.strip(),
                    "comunicacao": comunicacao.strip(),
                    "status": status,
                    "fonte": fonte.strip() or f"Position Paper – reunião de {data_reuniao.strftime('%d/%m/%Y')}",
                }
                reunioes.append(novo)
                save_data(reunioes)
                st.success("Registro salvo com sucesso.")
