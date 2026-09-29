import json
import re
import unicodedata
from datetime import date, datetime
from io import BytesIO
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None

try:
    from docx import Document
except Exception:
    Document = None

st.set_page_config(
    page_title="IPA – Construção de Temas",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
ASSET_DIR = BASE_DIR / "assets"
DATA_DIR.mkdir(exist_ok=True)
ASSET_DIR.mkdir(exist_ok=True)
DATA_FILE = DATA_DIR / "reunioes.json"
COMM_FILE = DATA_DIR / "comissoes.json"
LOGO_FILE = ASSET_DIR / "logo_ipa_card.png"

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

KEYWORDS = {
    "Alimentação e Saúde": ["alimentação", "alimentos", "saúde", "rotulagem", "nutrição"],
    "Ambiental": ["ambiental", "meio ambiente", "licenciamento", "clima", "carbono", "reserva legal"],
    "Bioenergia": ["bioenergia", "biocombustível", "etanol", "biodiesel", "biometano", "renovabio"],
    "Conselho Jurídico": ["jurídico", "stf", "constitucional", "judicialização", "parecer"],
    "Defesa Animal": ["defesa animal", "sanidade animal", "aftosa", "aves", "suínos", "bovinos"],
    "Defesa Vegetal": ["defesa vegetal", "fitossanit", "bioinsumo", "praga", "defensivo"],
    "Direito de Propriedade": ["direito de propriedade", "propriedade rural", "marco temporal", "reforma agrária"],
    "Infraestrutura e Logística": ["infraestrutura", "logística", "rodovia", "ferrovia", "porto", "armazenagem"],
    "Política Agrícola": ["política agrícola", "crédito rural", "seguro rural", "plano safra", "endividamento", "renegociação", "pronaf", "psr"],
    "Relações Internacionais": ["relações internacionais", "comércio exterior", "exportação", "importação", "tarifa", "china", "mercosul"],
    "Trabalhista": ["trabalhista", "trabalho rural", "jornada", "emprego", "mão de obra", "nr-31"],
    "Tributária": ["tributária", "tributário", "imposto", "reforma tributária", "icms", "itr"],
}

TEMAS_REFERENCIA = [
    "Seguro Rural",
    "Crédito Rural",
    "Plano Safra",
    "Bioinsumos",
    "Renegociação de Dívidas Rurais",
    "Endividamento Rural",
    "Profert",
    "Licenciamento Ambiental",
    "Reforma Tributária",
    "Marco Temporal",
    "Combustível do Futuro",
    "Regularização Ambiental",
    "Jornada de Trabalho",
]

PALETTE = {
    "navy": "#233f88",
    "blue": "#4269b1",
    "light": "#5a86c8",
    "bg": "#f4f7fb",
    "card": "#ffffff",
    "text": "#183153",
    "muted": "#64748b",
    "line": "#d9e3f1",
    "accent": "#e8eef8",
}


def inject_css():
    st.markdown(
        f"""
        <style>
            :root {{
                --navy: {PALETTE['navy']};
                --blue: {PALETTE['blue']};
                --light: {PALETTE['light']};
                --bg: {PALETTE['bg']};
                --card: {PALETTE['card']};
                --text: {PALETTE['text']};
                --muted: {PALETTE['muted']};
                --line: {PALETTE['line']};
                --accent: {PALETTE['accent']};
            }}
            .stApp {{ background: linear-gradient(180deg, #f7f9fc 0%, #eef4fb 100%); color: var(--text); }}
            [data-testid="stSidebar"] {{ background: linear-gradient(180deg, #163368 0%, #233f88 60%, #2f5aa6 100%); }}
            [data-testid="stSidebar"] * {{ color: white !important; }}
            [data-testid="stSidebarNav"] {{ display:none; }}
            .block-container {{ padding-top: 1.6rem; padding-bottom: 2rem; }}
            h1, h2, h3 {{ color: var(--navy); letter-spacing: -0.02em; }}
            .hero {{
                background: linear-gradient(135deg, rgba(35,63,136,0.98) 0%, rgba(66,105,177,0.96) 70%, rgba(90,134,200,0.92) 100%);
                border-radius: 22px; padding: 1.6rem 1.8rem; color: white; margin-bottom: 1.1rem;
                box-shadow: 0 20px 40px rgba(35,63,136,0.14);
            }}
            .hero h1, .hero p, .hero h3 {{ color: white !important; margin-bottom: 0.35rem; }}
            .subtle {{ color: rgba(255,255,255,0.85) !important; }}
            .panel {{ background: var(--card); border: 1px solid var(--line); border-radius: 18px; padding: 1rem 1.1rem; box-shadow: 0 10px 30px rgba(16, 24, 40, .05); }}
            .metric-card {{ background: var(--card); border: 1px solid var(--line); border-radius: 18px; padding: 1rem 1.1rem; }}
            .tag {{ display:inline-block; padding: 0.25rem 0.6rem; border-radius: 999px; background: var(--accent); color: var(--navy); font-size: 0.82rem; margin-right: 0.35rem; margin-bottom: 0.35rem; border: 1px solid var(--line); }}
            .source {{ color: var(--muted); font-size: 0.88rem; }}
            .empty {{ background: rgba(255,255,255,0.8); border: 1px dashed var(--line); border-radius: 18px; padding: 1.2rem; }}
            .section-title {{ font-size: 1.02rem; font-weight: 700; color: var(--navy); margin-bottom: 0.45rem; }}
            .small-note {{ color: var(--muted); font-size: .88rem; }}
            .stButton > button {{ border-radius: 12px; border: 1px solid transparent; min-height: 2.75rem; font-weight: 600; }}
            .stButton > button[kind="primary"] {{ background: linear-gradient(135deg, var(--navy), var(--blue)); }}
            .stTextInput input, .stTextArea textarea, .stDateInput input, .stMultiSelect div[data-baseweb="select"], .stSelectbox div[data-baseweb="select"] {{ border-radius: 12px !important; }}
            div[data-testid="stMetric"] {{ background: var(--card); border: 1px solid var(--line); border-radius: 18px; padding: 0.8rem 1rem; }}
            div[data-testid="stExpander"] {{ background: rgba(255,255,255,.86); border: 1px solid var(--line); border-radius: 16px; }}
            div[data-testid="stExpander"] details summary p {{ font-weight: 600; color: var(--navy); }}
            .search-box {{ background: rgba(255,255,255,.84); border: 1px solid var(--line); border-radius: 18px; padding: 1rem; }}
            .record-wrap {{ background: rgba(255,255,255,.82); border: 1px solid var(--line); border-radius: 18px; padding: 1rem; margin-bottom: 1rem; box-shadow: 0 8px 24px rgba(16,24,40,.04); }}
            hr {{ border-color: var(--line); }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def norm(text):
    text = unicodedata.normalize("NFD", str(text or ""))
    return "".join(c for c in text if unicodedata.category(c) != "Mn").lower()


def load_json(path: Path, default):
    if not path.exists():
        path.write_text(json.dumps(default, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def extract_text(uploaded_file):
    raw = uploaded_file.getvalue()
    name = uploaded_file.name.lower()
    if name.endswith(".txt"):
        return raw.decode("utf-8", errors="ignore")
    if name.endswith(".docx"):
        if not Document:
            raise RuntimeError("Leitura DOCX indisponível.")
        doc = Document(BytesIO(raw))
        parts = [p.text for p in doc.paragraphs if p.text.strip()]
        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                if row_text:
                    parts.append(row_text)
        return "\n".join(parts)
    if name.endswith(".pdf"):
        if not PdfReader:
            raise RuntimeError("Leitura PDF indisponível.")
        reader = PdfReader(BytesIO(raw))
        return "\n\n".join((page.extract_text() or "") for page in reader.pages)
    return ""


def find_date(text):
    patterns = [
        r"\b(\d{1,2})[/-](\d{1,2})[/-](20\d{2})\b",
        r"\b(20\d{2})-(\d{1,2})-(\d{1,2})\b",
    ]
    match = re.search(patterns[0], text)
    if match:
        try:
            return date(int(match.group(3)), int(match.group(2)), int(match.group(1)))
        except Exception:
            pass
    match = re.search(patterns[1], text)
    if match:
        try:
            return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except Exception:
            pass
    return date.today()


def detect_commissions(text, official):
    ntext = norm(text)
    scored = []
    for commission in official:
        score = 10 if norm(commission) in ntext else 0
        for kw in KEYWORDS.get(commission, []):
            score += min(ntext.count(norm(kw)), 5)
        if score:
            scored.append((score, commission))
    scored.sort(reverse=True)
    if not scored:
        return [], "Baixa"
    max_score = scored[0][0]
    picks = [c for s, c in scored if s >= max(2, max_score * 0.5)][:4]
    confidence = "Alta" if max_score >= 10 else "Média" if max_score >= 3 else "Baixa"
    return picks, confidence


def detect_theme(text, existing_themes):
    ntext = norm(text)
    # Primeiro tenta ler o tema diretamente do cabeçalho padrão dos papers.
    first_lines = [x.strip() for x in text.splitlines()[:8] if x.strip()]
    for line in first_lines:
        clean = re.sub(r"[*_]", "", line).strip()
        match = re.search(r"(?i)PAPER\s*\|\s*(.+?)(?:\s+IPA)?\s*[-–—]\s*\d{1,2}/\d{1,2}/20\d{2}", clean)
        if match:
            header = match.group(1).strip()
            header = re.sub(r"(?i)^GT\s+(?:DA|DE|DO|DAS|DOS)\s+", "", header).strip()
            header = re.sub(r"(?i)^COMISS[AÃ]O\s+(?:DA|DE|DO|DAS|DOS)\s+", "", header).strip()
            for theme in list(dict.fromkeys(existing_themes + TEMAS_REFERENCIA)):
                if norm(theme) in norm(header) or norm(header) in norm(theme):
                    return theme, "Alta"
            if 3 <= len(header) <= 100:
                return header.title(), "Alta"

    hits = []
    for theme in list(dict.fromkeys(existing_themes + TEMAS_REFERENCIA)):
        count = ntext.count(norm(theme))
        if count:
            hits.append((count, theme))
    if hits:
        hits.sort(reverse=True)
        return hits[0][1], ("Alta" if hits[0][0] >= 2 else "Média")
    for line in text.splitlines()[:35]:
        line = re.sub(r"\s+", " ", line).strip(" -–—:•")
        if 5 <= len(line) <= 100 and 2 <= len(line.split()) <= 14:
            return line, "Baixa"
    return "Novo tema", "Baixa"


def normalize_heading(line):
    line = re.sub(r"[*_]", "", str(line or ""))
    line = re.sub(r"^[\s🔹📌⚠️✅➡️▪️•\-–—]+", "", line).strip()
    line = re.sub(r"\s+", " ", line)
    return norm(line)


def parse_paper_blocks(text):
    """Reconhece o formato real dos papers enviados por WhatsApp."""
    lines = [x.rstrip() for x in text.splitlines()]
    blocks = {"introducao": [], "posicoes": [], "encaminhamentos": [], "importante": [], "comunicacao": [], "observacoes": []}
    current = "introducao"
    title_skipped = False

    for raw in lines:
        stripped = raw.strip()
        if not stripped:
            if blocks[current] and blocks[current][-1] != "":
                blocks[current].append("")
            continue

        # pula apenas o cabeçalho PAPER | ... da introdução
        if not title_skipped and re.search(r"(?i)^\s*PAPER\s*\|", stripped):
            title_skipped = True
            continue

        heading = normalize_heading(stripped)
        if heading in {"posicoes das entidades", "posicionamento das entidades", "posicoes", "posicionamentos"}:
            current = "posicoes"
            continue
        if heading in {"encaminhamento", "encaminhamentos", "proximos passos", "deliberacoes"}:
            current = "encaminhamentos"
            continue
        if heading.startswith("importante") or heading.startswith("atencao"):
            current = "importante"
            # preserva texto após "Importante:" na mesma linha
            after = re.sub(r"(?i)^.*?(importante|atenção|atencao)\s*:\s*", "", stripped).strip()
            if after and norm(after) != heading:
                blocks[current].append(after)
            continue
        if heading in {"comunicacao", "demanda para comunicacao", "demanda comunicacao"}:
            current = "comunicacao"
            continue
        if heading in {"observacao", "observacoes", "observacao institucional", "observacoes institucionais"}:
            current = "observacoes"
            continue

        blocks[current].append(stripped)

    def collapse(rows):
        out = []
        for row in rows:
            if row == "":
                if out and out[-1] != "":
                    out.append("")
            else:
                out.append(row)
        return "\n".join(out).strip()

    return {key: collapse(value) for key, value in blocks.items()}


def section(text, headings, max_chars=5000):
    # fallback para papers sem estrutura explícita
    lines = [x.strip() for x in text.splitlines()]
    for i, line in enumerate(lines):
        if any(norm(h) in norm(line) for h in headings):
            out = []
            for row in lines[i + 1 : i + 35]:
                if not row and out:
                    break
                if row:
                    out.append(row)
            if out:
                return "\n".join(out)[:max_chars]
    return ""


def load_secrets():
    try:
        return st.secrets.get("GEMINI_API_KEY", ""), st.secrets.get("GEMINI_MODEL", "")
    except Exception:
        return "", ""


def extract_json(raw):
    raw = (raw or "").strip()
    raw = re.sub(r"^```(?:json)?", "", raw, flags=re.I).strip()
    raw = re.sub(r"```$", "", raw).strip()
    start, end = raw.find("{"), raw.rfind("}")
    if start >= 0 and end > start:
        raw = raw[start : end + 1]
    return json.loads(raw)


def analyze_local(text, official, existing_themes):
    commissions, conf_c = detect_commissions(text, official)
    theme, conf_t = detect_theme(text, existing_themes)
    blocks = parse_paper_blocks(text)

    intro = blocks.get("introducao", "").strip()
    posicoes = blocks.get("posicoes", "").strip()
    encaminhamentos = blocks.get("encaminhamentos", "").strip()
    importante = blocks.get("importante", "").strip()
    observacoes = blocks.get("observacoes", "").strip()
    comunicacao = blocks.get("comunicacao", "").strip()

    # Resumo preserva a abertura factual do paper; posições ficam em campo próprio.
    summary = intro or section(text, ["resumo", "síntese", "discussão", "principais pontos"], 6000)
    if not summary:
        summary = re.sub(r"\s+", " ", text).strip()[:2500]

    if not encaminhamentos:
        encaminhamentos = section(text, ["encaminhamentos", "próximos passos", "deliberações"], 5000)
    if not comunicacao:
        comunicacao = section(text, ["comunicação", "demanda comunicação"], 3500)
    if not comunicacao:
        comunicacao = "Sem demanda específica identificada."

    # No formato IPA, o bloco "Importante" normalmente registra ressalva ou etapa institucional pendente.
    pontos_pendentes = importante
    observacao_institucional = observacoes or importante

    assuntos = []
    ntext = norm(text)
    if "diferimento" in ntext:
        assuntos.append("Diferimento da tributação")
    if "producao rural" in ntext or "produção rural" in text.lower():
        assuntos.append("Comercialização da produção rural")
    if "assembleia geral" in ntext:
        assuntos.append("Assembleia Geral do IPA")

    return {
        "data": find_date(text),
        "comissoes": commissions,
        "tema": theme,
        "resumo": summary,
        "posicoes_entidades": posicoes,
        "encaminhamentos": encaminhamentos,
        "comunicacao": comunicacao,
        "conf_c": conf_c,
        "conf_t": conf_t,
        "assuntos_relacionados": assuntos,
        "pontos_pendentes": pontos_pendentes,
        "observacao_institucional": observacao_institucional,
        "mudancas": "",
        "motor": "Análise local estruturada",
        "tema_existente": theme in existing_themes,
    }


def analyze_ai(text, official, existing_themes):
    key, model = load_secrets()
    if not key or not model:
        return None

    prompt = f"""Você analisa position papers de reuniões técnicas do Instituto Pensar Agro (IPA).
Extraia somente informações presentes no texto. Não invente.
Comissões válidas: {json.dumps(official, ensure_ascii=False)}
Temas já existentes: {json.dumps(existing_themes, ensure_ascii=False)}

Retorne exclusivamente JSON válido com:
data (AAAA-MM-DD ou null),
comissoes (array somente com nomes válidos),
tema (string curta e representativa),
tema_existente (boolean),
assuntos_relacionados (array),
resumo (síntese factual da abertura/contexto da reunião; não misture aqui as posições das entidades),
posicoes_entidades (registre separadamente as posições, consensos, divergências e entidades citadas),
encaminhamentos (todos os encaminhamentos encontrados),
comunicacao (todas as demandas para Comunicação; se não houver, "Sem demanda específica identificada."),
pontos_pendentes (pendências do tema),
observacao_institucional (ressalvas sobre instâncias decisórias, Diretoria, Assembleia, FPA, Congresso ou próximos níveis de decisão),
mudancas (avanços ou mudanças mencionados),
confianca_comissao ("Alta","Média","Baixa"),
confianca_tema ("Alta","Média","Baixa").

TEXTO INTEGRAL:
{text[:60000]}"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"},
    }
    response = requests.post(url, json=payload, timeout=60)
    response.raise_for_status()
    raw = response.json()["candidates"][0]["content"]["parts"][0]["text"]
    data = extract_json(raw)
    try:
        parsed_date = date.fromisoformat(data.get("data")) if data.get("data") else find_date(text)
    except Exception:
        parsed_date = find_date(text)

    return {
        "data": parsed_date,
        "comissoes": [c for c in data.get("comissoes", []) if c in official],
        "tema": data.get("tema") or "Novo tema",
        "resumo": data.get("resumo", ""),
        "posicoes_entidades": data.get("posicoes_entidades", ""),
        "encaminhamentos": data.get("encaminhamentos", ""),
        "comunicacao": data.get("comunicacao") or "Sem demanda específica identificada.",
        "conf_c": data.get("confianca_comissao", "Média"),
        "conf_t": data.get("confianca_tema", "Média"),
        "assuntos_relacionados": data.get("assuntos_relacionados", []),
        "pontos_pendentes": data.get("pontos_pendentes", ""),
        "observacao_institucional": data.get("observacao_institucional", ""),
        "mudancas": data.get("mudancas", ""),
        "tema_existente": bool(data.get("tema_existente", False)),
        "motor": "IA",
    }


def analyze(text, official, existing_themes):
    try:
        ai = analyze_ai(text, official, existing_themes)
        if ai:
            return ai
    except Exception:
        st.warning("A IA não pôde responder neste momento. A análise local foi usada.")
    return analyze_local(text, official, existing_themes)


def searchable_text(record):
    parts = [
        record.get("tema", ""),
        " ".join(record.get("comissoes", [])),
        " ".join(record.get("assuntos_relacionados", [])),
        record.get("resumo", ""),
        record.get("posicoes_entidades", ""),
        record.get("encaminhamentos", ""),
        record.get("pontos_pendentes", ""),
        record.get("observacao_institucional", ""),
        record.get("mudancas", ""),
        record.get("comunicacao", ""),
        record.get("fonte", ""),
        record.get("texto_original", ""),
    ]
    return "\n".join(str(x or "") for x in parts)


def score_record(record, query):
    words = [w for w in norm(query).split() if len(w) > 2]
    hay = norm(searchable_text(record))
    if not words:
        return 0
    score = 20 if norm(query) in hay else 0
    for word in words:
        count = hay.count(word)
        score += min(count, 10)
        if word in norm(record.get("tema", "")):
            score += 6
        if any(word in norm(c) for c in record.get("comissoes", [])):
            score += 3
    return score


def make_snippet(text, query, radius=250):
    raw = str(text or "").strip()
    if not raw:
        return ""
    nraw = norm(raw)
    terms = [w for w in norm(query).split() if len(w) > 2]
    pos = -1
    for term in terms:
        idx = nraw.find(term)
        if idx >= 0 and (pos < 0 or idx < pos):
            pos = idx
    if pos < 0:
        return re.sub(r"\s+", " ", raw)[:500]
    start = max(0, pos - radius)
    end = min(len(raw), pos + radius)
    snippet = re.sub(r"\s+", " ", raw[start:end]).strip()
    return ("… " if start else "") + snippet + (" …" if end < len(raw) else "")


def answer_from_results(query, results):
    key, model = load_secrets()
    if not key or not model or not results:
        return None
    docs = []
    for rec in results[:12]:
        docs.append(
            {
                "data": rec.get("data"),
                "tema": rec.get("tema"),
                "comissoes": rec.get("comissoes", []),
                "resumo": rec.get("resumo", ""),
                "posicoes_entidades": rec.get("posicoes_entidades", ""),
                "encaminhamentos": rec.get("encaminhamentos", ""),
                "pontos_pendentes": rec.get("pontos_pendentes", ""),
                "observacao_institucional": rec.get("observacao_institucional", ""),
                "mudancas": rec.get("mudancas", ""),
                "comunicacao": rec.get("comunicacao", ""),
                "texto_original": rec.get("texto_original", "")[:18000],
            }
        )
    prompt = f"""Responda à pergunta usando SOMENTE os registros abaixo da base interna do IPA.
Organize a resposta em: situação atual, histórico recente, encaminhamentos e pontos pendentes.
Se não houver base suficiente, diga isso. Não invente.
Pergunta: {query}
REGISTROS: {json.dumps(docs, ensure_ascii=False)}"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.1}}
    response = requests.post(url, json=payload, timeout=60)
    response.raise_for_status()
    return response.json()["candidates"][0]["content"]["parts"][0]["text"]


def metric_row(reunioes, comissoes):
    themes = sorted(set(r.get("tema", "") for r in reunioes if r.get("tema")))
    active_comms = sorted(set(c for r in reunioes for c in r.get("comissoes", [])))
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Temas", len(themes))
    c2.metric("Papers", len(reunioes))
    c3.metric("Comissões ativas", len(active_comms))
    comm_demand = len([r for r in reunioes if r.get("comunicacao") and "sem demanda" not in norm(r.get("comunicacao"))])
    c4.metric("Demandas para Comunicação", comm_demand)


def render_record(record, query=""):
    st.markdown('<div class="record-wrap">', unsafe_allow_html=True)
    st.subheader(f"{record.get('tema', 'Sem tema')} · {record.get('data', '')}")
    if record.get("comissoes"):
        tags = "".join([f'<span class="tag">{c}</span>' for c in record.get("comissoes", [])])
        st.markdown(tags, unsafe_allow_html=True)
    meta = f"Status: {record.get('status', '—')} · Origem: {record.get('origem', '—')}"
    if record.get("fonte"):
        meta += f" · Fonte: {record.get('fonte')}"
    st.markdown(f'<div class="source">{meta}</div>', unsafe_allow_html=True)

    if query:
        snippet = make_snippet(record.get("texto_original") or searchable_text(record), query)
        if snippet:
            st.markdown("**Trecho encontrado**")
            st.write(snippet)

    st.markdown("**Resumo da discussão**")
    st.write(record.get("resumo", ""))

    if record.get("posicoes_entidades"):
        st.markdown("**Posições das entidades**")
        st.write(record.get("posicoes_entidades"))

    c1, c2 = st.columns(2)
    with c1:
        if record.get("encaminhamentos"):
            st.markdown("**Encaminhamentos**")
            st.write(record.get("encaminhamentos"))
        if record.get("pontos_pendentes"):
            st.markdown("**Pontos pendentes**")
            st.write(record.get("pontos_pendentes"))
        if record.get("observacao_institucional"):
            st.markdown("**Observação institucional**")
            st.write(record.get("observacao_institucional"))
    with c2:
        if record.get("mudancas"):
            st.markdown("**Mudanças / avanços**")
            st.write(record.get("mudancas"))
        if record.get("comunicacao"):
            st.markdown("**Comunicação**")
            st.write(record.get("comunicacao"))

    if record.get("assuntos_relacionados"):
        st.caption("Assuntos relacionados: " + ", ".join(record.get("assuntos_relacionados", [])))

    original = record.get("texto_original", "")
    if original:
        with st.expander("Ver conteúdo integral do paper"):
            st.text_area(
                "Conteúdo integral",
                original,
                height=420,
                key=f"paper_{record.get('id')}_{record.get('data')}",
                disabled=True,
            )
    else:
        st.caption("Este registro não possui texto integral armazenado.")
    st.markdown("</div>", unsafe_allow_html=True)


def sidebar_logo_and_menu():
    if LOGO_FILE.exists():
        st.sidebar.image(str(LOGO_FILE), width=175)
    st.sidebar.markdown("### IPA – Construção de Temas")
    st.sidebar.caption("Memória das comissões, temas e encaminhamentos")
    return st.sidebar.radio(
        "Navegação",
        ["Pesquisar", "Temas", "Comissões", "Reuniões", "Radar", "Adicionar paper"],
        label_visibility="collapsed",
    )


def hero(title, subtitle):
    st.markdown(
        f"""
        <div class="hero">
            <h1>{title}</h1>
            <p class="subtle">{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------- boot ----------
inject_css()
comissoes = load_json(COMM_FILE, DEFAULT_COMISSOES)
reunioes = load_json(DATA_FILE, [])
for item in reunioes:
    if "comissoes" not in item:
        item["comissoes"] = [item.pop("comissao")] if item.get("comissao") else []
existing_themes = sorted(set(r.get("tema", "") for r in reunioes if r.get("tema")))
pagina = sidebar_logo_and_menu()

# ---------- pages ----------
if pagina == "Pesquisar":
    hero("Qual assunto você quer pesquisar hoje?", "Busque por tema, comissão, encaminhamentos ou dentro do conteúdo integral dos position papers.")
    metric_row(reunioes, comissoes)
    st.markdown('<div class="search-box">', unsafe_allow_html=True)
    with st.form("form_search"):
        q = st.text_input("Pergunte ou pesquise", placeholder="Ex.: O que já foi discutido sobre Seguro Rural? Qual o último encaminhamento sobre crédito rural?")
        c1, c2, c3 = st.columns(3)
        with c1:
            filtro_com = st.selectbox("Comissão", ["Todas"] + comissoes)
        with c2:
            filtro_tema = st.selectbox("Tema", ["Todos"] + existing_themes)
        with c3:
            filtro_status = st.selectbox("Status", ["Todos", "Em construção", "Em acompanhamento", "Consolidado", "Aguardando retorno", "Encerrado"])
        submitted = st.form_submit_button("Pesquisar", type="primary", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    if submitted and q.strip():
        results = []
        for rec in reunioes:
            if filtro_com != "Todas" and filtro_com not in rec.get("comissoes", []):
                continue
            if filtro_tema != "Todos" and filtro_tema != rec.get("tema"):
                continue
            if filtro_status != "Todos" and filtro_status != rec.get("status"):
                continue
            score = score_record(rec, q)
            if score > 0:
                results.append((score, rec))
        results.sort(key=lambda x: (x[0], x[1].get("data", "")), reverse=True)
        st.session_state["last_query"] = q
        st.session_state["search_results"] = [rec for _, rec in results]

    query = st.session_state.get("last_query", "")
    results = st.session_state.get("search_results", [])

    if query:
        if not results:
            st.markdown('<div class="empty"><strong>Nenhum conteúdo encontrado.</strong><br>Revise os termos ou tente uma busca mais ampla.</div>', unsafe_allow_html=True)
        else:
            st.markdown(f"### {len(results)} registro(s) encontrado(s)")
            answer = None
            try:
                answer = answer_from_results(query, results)
            except Exception:
                answer = None
            if answer:
                st.markdown('<div class="panel">', unsafe_allow_html=True)
                st.markdown("### Leitura consolidada da base")
                st.write(answer)
                st.caption("Resposta construída somente com os registros encontrados na base.")
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                temas = sorted(set(r.get("tema", "") for r in results if r.get("tema")))
                periodo = sorted([r.get("data", "") for r in results if r.get("data")])
                st.markdown('<div class="panel">', unsafe_allow_html=True)
                st.markdown("### Visão rápida")
                st.write(f"Temas relacionados: {', '.join(temas)}.")
                if periodo:
                    st.write(f"Período encontrado: {periodo[0]} a {periodo[-1]}.")
                st.caption("Quando a IA estiver configurada, esta área responderá a pergunta em texto corrido a partir dos papers encontrados.")
                st.markdown('</div>', unsafe_allow_html=True)
            st.divider()
            for rec in results:
                render_record(rec, query)

elif pagina == "Temas":
    hero("Temas", "Cada tema reúne o histórico das reuniões e das comissões relacionadas.")
    metric_row(reunioes, comissoes)
    if not existing_themes:
        st.markdown('<div class="empty">A base está limpa. Adicione os primeiros papers reais para começar.</div>', unsafe_allow_html=True)
    for theme in existing_themes:
        items = sorted([r for r in reunioes if r.get("tema") == theme], key=lambda x: x.get("data", ""), reverse=True)
        commissions = sorted(set(c for r in items for c in r.get("comissoes", [])))
        with st.expander(f"{theme} · {len(items)} registro(s) · {len(commissions)} comissão(ões)"):
            if commissions:
                st.markdown("**Comissões relacionadas**")
                st.markdown(" ".join([f'<span class="tag">{c}</span>' for c in commissions]), unsafe_allow_html=True)
            for rec in items:
                render_record(rec)

elif pagina == "Comissões":
    hero("Comissões", "Visualize os temas e papers organizados pela estrutura fixa do IPA.")
    metric_row(reunioes, comissoes)
    for commission in comissoes:
        items = sorted([r for r in reunioes if commission in r.get("comissoes", [])], key=lambda x: x.get("data", ""), reverse=True)
        themes = sorted(set(r.get("tema", "") for r in items if r.get("tema")))
        with st.expander(f"{commission} · {len(themes)} tema(s) · {len(items)} paper(s)"):
            if themes:
                st.markdown("**Temas nessa comissão**")
                st.markdown(" ".join([f'<span class="tag">{t}</span>' for t in themes]), unsafe_allow_html=True)
            else:
                st.caption("Nenhum tema registrado ainda.")
            for rec in items:
                render_record(rec)

elif pagina == "Reuniões":
    hero("Reuniões / Position Papers", "A base abaixo mostra os registros completos e o texto integral associado a cada paper.")
    metric_row(reunioes, comissoes)
    if not reunioes:
        st.markdown('<div class="empty">Nenhum paper cadastrado. A base foi limpa para receber os registros reais.</div>', unsafe_allow_html=True)
    for rec in sorted(reunioes, key=lambda x: x.get("data", ""), reverse=True):
        render_record(rec)

elif pagina == "Radar":
    hero("Radar", "Acompanhe rapidamente temas ativos, demandas para Comunicação e o estado atual da base.")
    metric_row(reunioes, comissoes)
    demandas = [r for r in reunioes if r.get("comunicacao") and "sem demanda" not in norm(r.get("comunicacao"))]
    recentes = sorted(reunioes, key=lambda x: x.get("data", ""), reverse=True)[:5]

    c1, c2 = st.columns([1.1, 1])
    with c1:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown("### Demandas para Comunicação")
        if demandas:
            for rec in sorted(demandas, key=lambda x: x.get("data", ""), reverse=True):
                st.markdown(f"**{rec.get('tema')} · {rec.get('data')}**")
                st.write(rec.get("comunicacao"))
                st.divider()
        else:
            st.caption("Nenhuma demanda registrada até o momento.")
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown("### Papers mais recentes")
        if recentes:
            for rec in recentes:
                st.markdown(f"**{rec.get('data')} · {rec.get('tema', 'Sem tema')}**")
                st.caption(", ".join(rec.get("comissoes", [])) or "Sem comissão")
                st.write((rec.get("resumo", "")[:240] + "…") if len(rec.get("resumo", "")) > 240 else rec.get("resumo", ""))
                st.divider()
        else:
            st.caption("A base ainda não possui papers reais cadastrados.")
        st.markdown('</div>', unsafe_allow_html=True)

else:
    hero("Adicionar paper", "Cole o texto completo ou envie o documento. O conteúdo integral será preservado na base.")
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    modo = st.radio("Como quer adicionar?", ["Enviar arquivo", "Colar texto"], horizontal=True)

    if modo == "Enviar arquivo":
        upload = st.file_uploader("Selecione PDF, DOCX ou TXT", type=["pdf", "docx", "txt"])
        if upload and st.button("Ler e analisar documento", type="primary", use_container_width=True):
            try:
                text = extract_text(upload)
                if len(text.strip()) < 30:
                    st.error("Não foi possível extrair conteúdo suficiente desse arquivo.")
                else:
                    st.session_state["analysis"] = analyze(text, comissoes, existing_themes)
                    st.session_state["original_text"] = text
                    st.session_state["source_type"] = "Documento"
                    st.session_state["file_name"] = upload.name
            except Exception as exc:
                st.error(f"Erro ao ler o documento: {exc}")
    else:
        pasted = st.text_area("Cole aqui o position paper completo", height=360, placeholder="Cole todo o conteúdo recebido por WhatsApp, e-mail ou outro canal...")
        origin = st.selectbox("Origem", ["WhatsApp", "E-mail", "Outro"])
        st.caption(f"Caracteres capturados: {len(pasted):,}".replace(",", "."))
        if st.button("Analisar conteúdo completo", type="primary", use_container_width=True):
            if len(pasted.strip()) < 30:
                st.warning("Cole o conteúdo do paper antes de analisar.")
            else:
                st.session_state["analysis"] = analyze(pasted, comissoes, existing_themes)
                st.session_state["original_text"] = pasted
                st.session_state["source_type"] = origin
                st.session_state["file_name"] = ""

    analysis = st.session_state.get("analysis")
    if analysis:
        original_text = st.session_state.get("original_text", "")
        st.success(f"Conteúdo capturado: {len(original_text):,} caracteres.".replace(",", "."))
        with st.expander("Conferir conteúdo integral capturado"):
            st.text_area("Paper original", original_text, height=420, disabled=True)

        st.markdown("### Revisar classificação e análise")
        st.caption(f"Motor: {analysis.get('motor', 'Análise local')} · Confiança na comissão: {analysis['conf_c']} · Confiança no tema: {analysis['conf_t']}")
        if analysis.get("tema_existente"):
            st.info("O tema identificado já existe na base. Este paper será acrescentado ao histórico.")
        else:
            st.info("O sistema considera este um novo tema. Revise antes de salvar.")

        with st.form("review_form"):
            c1, c2 = st.columns(2)
            with c1:
                meeting_date = st.date_input("Data da reunião", analysis["data"])
                selected_commissions = st.multiselect("Comissão(ões)", comissoes, default=[x for x in analysis["comissoes"] if x in comissoes])
                theme = st.text_input("Tema principal", analysis["tema"])
            with c2:
                status = st.selectbox("Status", ["Em construção", "Em acompanhamento", "Consolidado", "Aguardando retorno", "Encerrado"])
                options = ["Documento", "WhatsApp", "E-mail", "Outro"]
                source_type = st.session_state.get("source_type", "Documento")
                source_final = st.selectbox("Origem", options, index=options.index(source_type) if source_type in options else 0)
                source = st.text_input("Fonte", f"Position Paper – {st.session_state.get('file_name') or source_final} – {meeting_date.strftime('%d/%m/%Y')}")

            related = st.text_input("Assuntos relacionados", ", ".join(analysis.get("assuntos_relacionados", [])))
            summary = st.text_area("Resumo da discussão", analysis["resumo"], height=220)
            positions = st.text_area("Posições das entidades", analysis.get("posicoes_entidades", ""), height=150)
            actions = st.text_area("Encaminhamentos", analysis["encaminhamentos"], height=150)
            pending = st.text_area("Pontos pendentes", analysis.get("pontos_pendentes", ""), height=120)
            institutional = st.text_area("Observação institucional", analysis.get("observacao_institucional", ""), height=120)
            changes = st.text_area("Mudanças / avanços identificados", analysis.get("mudancas", ""), height=120)
            communication = st.text_area("Demanda para Comunicação", analysis["comunicacao"], height=120)

            if st.form_submit_button("Salvar paper completo", type="primary", use_container_width=True):
                if not selected_commissions or not theme.strip():
                    st.error("Confirme ao menos a comissão e o tema.")
                elif not original_text.strip():
                    st.error("O conteúdo integral do paper não foi capturado.")
                else:
                    new_record = {
                        "id": max([r.get("id", 0) for r in reunioes], default=0) + 1,
                        "data": meeting_date.isoformat(),
                        "comissoes": selected_commissions,
                        "tema": theme.strip(),
                        "resumo": summary.strip(),
                        "posicoes_entidades": positions.strip(),
                        "encaminhamentos": actions.strip(),
                        "pontos_pendentes": pending.strip(),
                        "observacao_institucional": institutional.strip(),
                        "mudancas": changes.strip(),
                        "assuntos_relacionados": [x.strip() for x in related.split(",") if x.strip()],
                        "comunicacao": communication.strip(),
                        "status": status,
                        "origem": source_final,
                        "fonte": source.strip(),
                        "texto_original": original_text,
                        "criado_em": datetime.now().isoformat(timespec="seconds"),
                    }
                    reunioes.append(new_record)
                    save_json(DATA_FILE, reunioes)
                    for key in ["analysis", "original_text", "source_type", "file_name"]:
                        st.session_state.pop(key, None)
                    st.success("Paper completo registrado na base.")
                    st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
