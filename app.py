import streamlit as st
import pandas as pd
from datetime import date
from pathlib import Path
from io import BytesIO
import json, re, unicodedata
import requests

try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None
try:
    from docx import Document
except Exception:
    Document = None

st.set_page_config(page_title="IPA – Construção de Temas", page_icon="🧭", layout="wide")

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
DATA_FILE = DATA_DIR / "reunioes.json"
COMM_FILE = DATA_DIR / "comissoes.json"

DEFAULT_COMISSOES = [
    "Alimentação e Saúde","Ambiental","Bioenergia","Conselho Jurídico",
    "Defesa Animal","Defesa Vegetal","Direito de Propriedade",
    "Infraestrutura e Logística","Política Agrícola","Relações Internacionais",
    "Trabalhista","Tributária"
]

KEYWORDS = {
    "Alimentação e Saúde":["alimentação","alimentos","saúde","rotulagem","nutrição"],
    "Ambiental":["ambiental","meio ambiente","licenciamento","clima","carbono","reserva legal"],
    "Bioenergia":["bioenergia","biocombustível","etanol","biodiesel","biometano","renovabio"],
    "Conselho Jurídico":["jurídico","stf","constitucional","judicialização","parecer"],
    "Defesa Animal":["defesa animal","sanidade animal","aftosa","aves","suínos","bovinos"],
    "Defesa Vegetal":["defesa vegetal","fitossanit","bioinsumo","praga","defensivo"],
    "Direito de Propriedade":["direito de propriedade","propriedade rural","marco temporal","reforma agrária"],
    "Infraestrutura e Logística":["infraestrutura","logística","rodovia","ferrovia","porto","armazenagem"],
    "Política Agrícola":["política agrícola","crédito rural","seguro rural","plano safra","endividamento","renegociação","pronaf","psr"],
    "Relações Internacionais":["relações internacionais","comércio exterior","exportação","importação","tarifa","china","mercosul"],
    "Trabalhista":["trabalhista","trabalho rural","jornada","emprego","mão de obra","nr-31"],
    "Tributária":["tributária","tributário","imposto","reforma tributária","icms","itr"],
}

TEMAS = ["Seguro Rural","Crédito Rural","Plano Safra","Bioinsumos","Renegociação de Dívidas Rurais",
         "Endividamento Rural","Profert","Licenciamento Ambiental","Reforma Tributária","Marco Temporal",
         "Combustível do Futuro","Regularização Ambiental","Jornada de Trabalho"]

def norm(x):
    x = unicodedata.normalize("NFD", str(x or ""))
    return "".join(c for c in x if unicodedata.category(c)!="Mn").lower()

def load_json(path, default):
    if not path.exists():
        path.write_text(json.dumps(default, ensure_ascii=False, indent=2), encoding="utf-8")
    return json.loads(path.read_text(encoding="utf-8"))

def save_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def extract_text(file):
    raw=file.getvalue(); name=file.name.lower()
    if name.endswith(".txt"):
        return raw.decode("utf-8", errors="ignore")
    if name.endswith(".docx"):
        if not Document: raise RuntimeError("Leitura DOCX indisponível.")
        d=Document(BytesIO(raw))
        return "\n".join(p.text for p in d.paragraphs if p.text.strip())
    if name.endswith(".pdf"):
        if not PdfReader: raise RuntimeError("Leitura PDF indisponível.")
        return "\n".join((p.extract_text() or "") for p in PdfReader(BytesIO(raw)).pages)
    return ""

def find_date(text):
    m=re.search(r"\b(\d{1,2})[/-](\d{1,2})[/-](20\d{2})\b", text)
    if m:
        try: return date(int(m.group(3)),int(m.group(2)),int(m.group(1)))
        except: pass
    return date.today()

def detect_commissions(text, official):
    n=norm(text); scored=[]
    for c in official:
        score=8 if norm(c) in n else 0
        for k in KEYWORDS.get(c,[]): score += min(n.count(norm(k)),4)
        if score: scored.append((score,c))
    scored.sort(reverse=True)
    if not scored: return [],"Baixa"
    mx=scored[0][0]
    picks=[c for s,c in scored if s>=max(2,mx*.55)][:3]
    return picks, ("Alta" if mx>=8 else "Média" if mx>=3 else "Baixa")

def detect_theme(text, existing):
    n=norm(text); hits=[]
    for t in list(dict.fromkeys(existing+TEMAS)):
        count=n.count(norm(t))
        if count: hits.append((count,t))
    if hits:
        hits.sort(reverse=True)
        return hits[0][1], ("Alta" if hits[0][0]>=2 else "Média")
    for line in text.splitlines()[:25]:
        line=re.sub(r"\s+"," ",line).strip(" -–—:•")
        if 5<=len(line)<=90 and len(line.split())<=12:
            return line,"Baixa"
    return "Novo tema","Baixa"

def section(text, headings):
    lines=[x.strip() for x in text.splitlines()]
    for i,l in enumerate(lines):
        if any(norm(h) in norm(l) for h in headings):
            out=[]
            for x in lines[i+1:i+12]:
                if not x and out: break
                if x: out.append(x)
            if out: return " ".join(out)[:1800]
    return ""

def analyze_local(text, official, existing):
    cs,cc=detect_commissions(text,official)
    tema,ct=detect_theme(text,existing)
    resumo=section(text,["resumo","síntese","discussão","principais pontos"])
    if not resumo: resumo=re.sub(r"\s+"," ",text).strip()[:1200]
    enc=section(text,["encaminhamentos","próximos passos","deliberações"])
    com=section(text,["comunicação","demanda comunicação"]) or "Sem demanda específica identificada."
    return {"data":find_date(text),"comissoes":cs,"tema":tema,"resumo":resumo,
            "encaminhamentos":enc,"comunicacao":com,"conf_c":cc,"conf_t":ct,
            "assuntos_relacionados":[],"pontos_pendentes":"","mudancas":"","motor":"Análise local"}

def _extract_json(raw):
    raw=(raw or "").strip()
    raw=re.sub(r"^\`\`\`(?:json)?","",raw,flags=re.I).strip()
    raw=re.sub(r"\`\`\`$","",raw).strip()
    start=raw.find("{"); end=raw.rfind("}")
    if start>=0 and end>start: raw=raw[start:end+1]
    return json.loads(raw)

def analyze_ai(text, official, existing):
    key=st.secrets.get("GEMINI_API_KEY","")
    model=st.secrets.get("GEMINI_MODEL","")
    if not key or not model:
        return None
    prompt=f"""Você analisa position papers de reuniões técnicas do Instituto Pensar Agro (IPA).
Extraia APENAS fatos presentes no texto. Não invente informações.
Comissões válidas: {json.dumps(official,ensure_ascii=False)}
Temas já existentes: {json.dumps(existing,ensure_ascii=False)}

Retorne exclusivamente JSON válido com:
data (AAAA-MM-DD ou null),
comissoes (array, somente nomes da lista válida),
tema (string curta),
tema_existente (boolean),
assuntos_relacionados (array de strings curtas),
resumo (síntese objetiva do que foi discutido),
encaminhamentos (texto),
comunicacao (demanda para Comunicação; se não houver, escreva "Sem demanda específica identificada."),
pontos_pendentes (texto),
mudancas (o que o documento indica como avanço, mudança ou novidade; se não for possível comparar, deixe vazio),
confianca_comissao ("Alta","Média","Baixa"),
confianca_tema ("Alta","Média","Baixa").

TEXTO:
{text[:22000]}"""
    url=f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    payload={"contents":[{"parts":[{"text":prompt}]}],
             "generationConfig":{"temperature":0.1,"responseMimeType":"application/json"}}
    r=requests.post(url,json=payload,timeout=45)
    r.raise_for_status()
    raw=r.json()["candidates"][0]["content"]["parts"][0]["text"]
    data=_extract_json(raw)
    d=data.get("data")
    try: parsed=date.fromisoformat(d) if d else find_date(text)
    except: parsed=find_date(text)
    valid=[c for c in data.get("comissoes",[]) if c in official]
    return {
        "data":parsed,"comissoes":valid,"tema":data.get("tema") or "Novo tema",
        "resumo":data.get("resumo",""),"encaminhamentos":data.get("encaminhamentos",""),
        "comunicacao":data.get("comunicacao") or "Sem demanda específica identificada.",
        "conf_c":data.get("confianca_comissao","Média"),"conf_t":data.get("confianca_tema","Média"),
        "assuntos_relacionados":data.get("assuntos_relacionados",[]),
        "pontos_pendentes":data.get("pontos_pendentes",""),"mudancas":data.get("mudancas",""),
        "tema_existente":bool(data.get("tema_existente",False)),"motor":"IA"
    }

def analyze(text, official, existing):
    try:
        ai=analyze_ai(text,official,existing)
        if ai: return ai
    except Exception as e:
        st.warning(f"A análise por IA não pôde ser concluída. Usando análise local. ({e})")
    return analyze_local(text,official,existing)

comissoes=load_json(COMM_FILE,DEFAULT_COMISSOES)
reunioes=load_json(DATA_FILE,[])
for r in reunioes:
    if "comissoes" not in r:
        r["comissoes"]=[r.pop("comissao")] if r.get("comissao") else []
existing=sorted(set(r.get("tema","") for r in reunioes if r.get("tema")))

st.sidebar.title("IPA")
st.sidebar.caption("Construção de Temas")
pagina=st.sidebar.radio("",["Pesquisar","Temas","Comissões","Reuniões","Radar","Adicionar position paper"])

if pagina=="Pesquisar":
    st.title("Qual assunto você quer pesquisar hoje?")
    q=st.text_input("Pesquisar",placeholder="Ex.: Seguro Rural, bioinsumos, crédito rural...")
    if q:
        achados=[r for r in reunioes if norm(q) in norm(json.dumps(r,ensure_ascii=False))]
        if not achados: st.info("Nenhum registro encontrado.")
        for r in sorted(achados,key=lambda x:x.get("data",""),reverse=True):
            with st.container(border=True):
                st.subheader(r.get("tema","Sem tema"))
                st.caption(f"{r.get('data','')} • {' • '.join(r.get('comissoes',[]))}")
                st.write(r.get("resumo",""))
                if r.get("encaminhamentos"): st.markdown("**Encaminhamentos:** "+r["encaminhamentos"])

elif pagina=="Temas":
    st.title("Temas")
    for tema in existing:
        itens=[r for r in reunioes if r.get("tema")==tema]
        coms=sorted(set(c for r in itens for c in r.get("comissoes",[])))
        with st.expander(f"{tema} · {len(itens)} registro(s)"):
            st.caption("Comissões: "+(", ".join(coms) or "—"))
            for r in sorted(itens,key=lambda x:x.get("data",""),reverse=True):
                st.markdown(f"**{r.get('data','')}** — {r.get('resumo','')}")

elif pagina=="Comissões":
    st.title("Comissões")
    for c in comissoes:
        itens=[r for r in reunioes if c in r.get("comissoes",[])]
        temas=sorted(set(r.get("tema","") for r in itens if r.get("tema")))
        with st.expander(f"{c} · {len(temas)} tema(s) · {len(itens)} reunião(ões)"):
            if temas: st.write(", ".join(temas))
            else: st.caption("Nenhum tema registrado ainda.")

elif pagina=="Reuniões":
    st.title("Reuniões")
    if reunioes:
        df=pd.DataFrame([{"Data":r.get("data"),"Tema":r.get("tema"),"Comissões":", ".join(r.get("comissoes",[])),
                          "Status":r.get("status"),"Origem":r.get("origem","Documento")} for r in reunioes])
        st.dataframe(df,hide_index=True,use_container_width=True)
    else: st.info("Nenhuma reunião registrada.")

elif pagina=="Radar":
    st.title("Radar")
    c1,c2=st.columns(2)
    c1.metric("Temas",len(existing)); c2.metric("Reuniões",len(reunioes))
    demandas=[r for r in reunioes if r.get("comunicacao") and "sem demanda" not in norm(r.get("comunicacao"))]
    st.subheader("Demandas para Comunicação")
    if demandas:
        for r in demandas: st.markdown(f"**{r.get('tema')}** — {r.get('comunicacao')}")
    else: st.info("Nenhuma demanda registrada.")

else:
    st.title("Adicionar position paper")
    st.caption("Envie um documento ou cole o conteúdo recebido por WhatsApp/e-mail. Você revisa tudo antes de salvar.")
    modo=st.radio("Como quer adicionar?",["Enviar arquivo","Colar texto"],horizontal=True)
    if modo=="Enviar arquivo":
        arq=st.file_uploader("PDF, DOCX ou TXT",type=["pdf","docx","txt"])
        if arq and st.button("Analisar documento",type="primary"):
            try:
                texto=extract_text(arq)
                if not texto.strip(): st.error("Não foi possível extrair texto.")
                else:
                    st.session_state["analise"]=analyze(texto,comissoes,existing)
                    st.session_state["texto"]=texto; st.session_state["origem"]="Documento"; st.session_state["nome"]=arq.name
            except Exception as e: st.error(str(e))
    else:
        texto_colado=st.text_area("Cole aqui o position paper ou relato da reunião",height=300,
                                  placeholder="Cole o texto recebido pelo WhatsApp, e-mail ou outro canal...")
        origem_sel=st.selectbox("Origem",["WhatsApp","E-mail","Outro"])
        if st.button("Analisar conteúdo",type="primary"):
            if not texto_colado.strip(): st.warning("Cole algum conteúdo antes de analisar.")
            else:
                st.session_state["analise"]=analyze(texto_colado,comissoes,existing)
                st.session_state["texto"]=texto_colado; st.session_state["origem"]=origem_sel; st.session_state["nome"]=""

    a=st.session_state.get("analise")
    if a:
        st.divider(); st.subheader("Revise as informações identificadas")
        st.caption(f"Motor: {a.get('motor','Análise local')} · Confiança na comissão: {a['conf_c']} · Confiança no tema: {a['conf_t']}")
        if a.get("tema_existente") is True:
            st.success("O tema identificado já existe na base e pode receber este novo registro.")
        elif a.get("tema_existente") is False and a.get("motor")=="IA":
            st.info("A IA considera este um novo tema. Revise antes de salvar.")
        with st.form("revisao"):
            c1,c2=st.columns(2)
            with c1:
                dt=st.date_input("Data da reunião",a["data"])
                cs=st.multiselect("Comissão(ões)",comissoes,default=[x for x in a["comissoes"] if x in comissoes])
                tema=st.text_input("Tema principal",a["tema"])
            with c2:
                status=st.selectbox("Status",["Em construção","Em acompanhamento","Consolidado","Aguardando retorno","Encerrado"])
                origem_final=st.selectbox("Origem",["Documento","WhatsApp","E-mail","Outro"],
                    index=["Documento","WhatsApp","E-mail","Outro"].index(st.session_state.get("origem","Documento")))
                fonte=st.text_input("Fonte",f"Position Paper – {st.session_state.get('nome') or origem_final} – {dt.strftime('%d/%m/%Y')}")
            assuntos=st.text_input("Assuntos relacionados",", ".join(a.get("assuntos_relacionados",[])))
            resumo=st.text_area("Resumo da discussão",a["resumo"],height=180)
            enc=st.text_area("Encaminhamentos",a["encaminhamentos"],height=120)
            pend=st.text_area("Pontos pendentes",a.get("pontos_pendentes",""),height=100)
            mud=st.text_area("Mudanças / avanços identificados",a.get("mudancas",""),height=100)
            com=st.text_area("Demanda para Comunicação",a["comunicacao"],height=100)
            if st.form_submit_button("Confirmar e salvar",type="primary",use_container_width=True):
                if not cs or not tema.strip() or not resumo.strip():
                    st.error("Confirme comissão, tema e resumo.")
                else:
                    novo={"id":max([r.get("id",0) for r in reunioes],default=0)+1,
                          "data":dt.isoformat(),"comissoes":cs,"tema":tema.strip(),"resumo":resumo.strip(),
                          "encaminhamentos":enc.strip(),"pontos_pendentes":pend.strip(),"mudancas":mud.strip(),
                          "assuntos_relacionados":[x.strip() for x in assuntos.split(",") if x.strip()],
                          "comunicacao":com.strip(),"status":status,
                          "origem":origem_final,"fonte":fonte.strip(),"texto_original":st.session_state.get("texto","")}
                    reunioes.append(novo); save_json(DATA_FILE,reunioes)
                    for k in ["analise","texto","origem","nome"]: st.session_state.pop(k,None)
                    st.success("Position paper registrado.")
                    st.rerun()
