import streamlit as st
import pandas as pd
from datetime import date, datetime
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

TEMAS = [
    "Seguro Rural","Crédito Rural","Plano Safra","Bioinsumos",
    "Renegociação de Dívidas Rurais","Endividamento Rural","Profert",
    "Licenciamento Ambiental","Reforma Tributária","Marco Temporal",
    "Combustível do Futuro","Regularização Ambiental","Jornada de Trabalho"
]

def norm(x):
    x = unicodedata.normalize("NFD", str(x or ""))
    return "".join(c for c in x if unicodedata.category(c)!="Mn").lower()

def load_json(path, default):
    if not path.exists():
        path.write_text(json.dumps(default, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default

def save_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def extract_text(file):
    raw=file.getvalue(); name=file.name.lower()
    if name.endswith(".txt"):
        return raw.decode("utf-8", errors="ignore")
    if name.endswith(".docx"):
        if not Document:
            raise RuntimeError("Leitura DOCX indisponível.")
        d=Document(BytesIO(raw))
        parts=[]
        for p in d.paragraphs:
            if p.text.strip(): parts.append(p.text)
        for table in d.tables:
            for row in table.rows:
                txt=" | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                if txt: parts.append(txt)
        return "\n".join(parts)
    if name.endswith(".pdf"):
        if not PdfReader:
            raise RuntimeError("Leitura PDF indisponível.")
        reader=PdfReader(BytesIO(raw))
        return "\n\n".join((p.extract_text() or "") for p in reader.pages)
    return ""

def find_date(text):
    patterns=[
        r"\b(\d{1,2})[/-](\d{1,2})[/-](20\d{2})\b",
        r"\b(20\d{2})-(\d{1,2})-(\d{1,2})\b"
    ]
    m=re.search(patterns[0], text)
    if m:
        try: return date(int(m.group(3)),int(m.group(2)),int(m.group(1)))
        except Exception: pass
    m=re.search(patterns[1], text)
    if m:
        try: return date(int(m.group(1)),int(m.group(2)),int(m.group(3)))
        except Exception: pass
    return date.today()

def detect_commissions(text, official):
    n=norm(text); scored=[]
    for c in official:
        score=10 if norm(c) in n else 0
        for k in KEYWORDS.get(c,[]):
            score += min(n.count(norm(k)),5)
        if score: scored.append((score,c))
    scored.sort(reverse=True)
    if not scored: return [],"Baixa"
    mx=scored[0][0]
    picks=[c for s,c in scored if s>=max(2,mx*.5)][:4]
    return picks, ("Alta" if mx>=10 else "Média" if mx>=3 else "Baixa")

def detect_theme(text, existing):
    n=norm(text); hits=[]
    for t in list(dict.fromkeys(existing+TEMAS)):
        count=n.count(norm(t))
        if count: hits.append((count,t))
    if hits:
        hits.sort(reverse=True)
        return hits[0][1], ("Alta" if hits[0][0]>=2 else "Média")
    for line in text.splitlines()[:35]:
        line=re.sub(r"\s+"," ",line).strip(" -–—:•")
        if 5<=len(line)<=100 and 2<=len(line.split())<=14:
            return line,"Baixa"
    return "Novo tema","Baixa"

def section(text, headings, max_chars=4000):
    lines=[x.strip() for x in text.splitlines()]
    for i,l in enumerate(lines):
        if any(norm(h) in norm(l) for h in headings):
            out=[]
            for x in lines[i+1:i+30]:
                if not x and out: break
                if x: out.append(x)
            if out: return "\n".join(out)[:max_chars]
    return ""

def analyze_local(text, official, existing):
    cs,cc=detect_commissions(text,official)
    tema,ct=detect_theme(text,existing)
    resumo=section(text,["resumo","síntese","discussão","principais pontos"],5000)
    if not resumo:
        clean=re.sub(r"\s+"," ",text).strip()
        resumo=clean[:2200]
    enc=section(text,["encaminhamentos","próximos passos","deliberações"],5000)
    com=section(text,["comunicação","demanda comunicação"],3000) or "Sem demanda específica identificada."
    return {
        "data":find_date(text),"comissoes":cs,"tema":tema,"resumo":resumo,
        "encaminhamentos":enc,"comunicacao":com,"conf_c":cc,"conf_t":ct,
        "assuntos_relacionados":[],"pontos_pendentes":"","mudancas":"",
        "motor":"Análise local","tema_existente":tema in existing
    }

def _extract_json(raw):
    raw=(raw or "").strip()
    raw=re.sub(r"^\`\`\`(?:json)?","",raw,flags=re.I).strip()
    raw=re.sub(r"\`\`\`$","",raw).strip()
    start=raw.find("{"); end=raw.rfind("}")
    if start>=0 and end>start: raw=raw[start:end+1]
    return json.loads(raw)

def gemini_config():
    try:
        return st.secrets.get("GEMINI_API_KEY",""), st.secrets.get("GEMINI_MODEL","")
    except Exception:
        return "",""

def analyze_ai(text, official, existing):
    key,model=gemini_config()
    if not key or not model: return None
    prompt=f"""Você analisa position papers de reuniões técnicas do Instituto Pensar Agro (IPA).
Extraia somente informações presentes no texto. Não invente.
Comissões válidas: {json.dumps(official,ensure_ascii=False)}
Temas já existentes: {json.dumps(existing,ensure_ascii=False)}

Retorne exclusivamente JSON válido com:
data (AAAA-MM-DD ou null),
comissoes (array somente com nomes válidos),
tema (string curta e representativa),
tema_existente (boolean),
assuntos_relacionados (array),
resumo (resumo completo e fiel, preservando os principais argumentos, posições e fatos),
encaminhamentos (todos os encaminhamentos encontrados),
comunicacao (todas as demandas para Comunicação; se não houver, "Sem demanda específica identificada."),
pontos_pendentes (pendências do tema),
mudancas (avanços ou mudanças mencionados),
confianca_comissao ("Alta","Média","Baixa"),
confianca_tema ("Alta","Média","Baixa").

TEXTO INTEGRAL:
{text[:60000]}"""
    url=f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    payload={"contents":[{"parts":[{"text":prompt}]}],
             "generationConfig":{"temperature":0.1,"responseMimeType":"application/json"}}
    r=requests.post(url,json=payload,timeout=60)
    r.raise_for_status()
    raw=r.json()["candidates"][0]["content"]["parts"][0]["text"]
    data=_extract_json(raw)
    try: parsed=date.fromisoformat(data.get("data")) if data.get("data") else find_date(text)
    except Exception: parsed=find_date(text)
    return {
        "data":parsed,
        "comissoes":[c for c in data.get("comissoes",[]) if c in official],
        "tema":data.get("tema") or "Novo tema",
        "resumo":data.get("resumo",""),
        "encaminhamentos":data.get("encaminhamentos",""),
        "comunicacao":data.get("comunicacao") or "Sem demanda específica identificada.",
        "conf_c":data.get("confianca_comissao","Média"),
        "conf_t":data.get("confianca_tema","Média"),
        "assuntos_relacionados":data.get("assuntos_relacionados",[]),
        "pontos_pendentes":data.get("pontos_pendentes",""),
        "mudancas":data.get("mudancas",""),
        "tema_existente":bool(data.get("tema_existente",False)),
        "motor":"IA"
    }

def analyze(text, official, existing):
    try:
        ai=analyze_ai(text,official,existing)
        if ai: return ai
    except Exception as e:
        st.warning("A IA não respondeu. A análise local foi usada neste registro.")
    return analyze_local(text,official,existing)

def searchable_text(r):
    fields=[
        r.get("tema","")," ".join(r.get("comissoes",[])),
        " ".join(r.get("assuntos_relacionados",[])),r.get("resumo",""),
        r.get("encaminhamentos",""),r.get("pontos_pendentes",""),
        r.get("mudancas",""),r.get("comunicacao",""),r.get("fonte",""),
        r.get("texto_original","")
    ]
    return "\n".join(str(x or "") for x in fields)

def score_record(r, query):
    words=[w for w in norm(query).split() if len(w)>2]
    hay=norm(searchable_text(r))
    if not words: return 0
    phrase=norm(query)
    score=20 if phrase and phrase in hay else 0
    for w in words:
        count=hay.count(w)
        score += min(count,10)
        if w in norm(r.get("tema","")): score += 6
        if any(w in norm(c) for c in r.get("comissoes",[])): score += 3
    return score

def make_snippet(text, query, radius=260):
    raw=str(text or "").strip()
    if not raw: return ""
    nraw=norm(raw); terms=[w for w in norm(query).split() if len(w)>2]
    pos=-1
    for t in terms:
        p=nraw.find(t)
        if p>=0 and (pos<0 or p<pos): pos=p
    if pos<0: return re.sub(r"\s+"," ",raw)[:520]
    start=max(0,pos-radius); end=min(len(raw),pos+radius)
    sn=re.sub(r"\s+"," ",raw[start:end]).strip()
    return ("… " if start else "")+sn+(" …" if end<len(raw) else "")

def ai_answer(query, results):
    key,model=gemini_config()
    if not key or not model or not results: return None
    docs=[]
    for r in results[:12]:
        docs.append({
            "data":r.get("data"),"tema":r.get("tema"),"comissoes":r.get("comissoes",[]),
            "resumo":r.get("resumo",""),"encaminhamentos":r.get("encaminhamentos",""),
            "pontos_pendentes":r.get("pontos_pendentes",""),"mudancas":r.get("mudancas",""),
            "comunicacao":r.get("comunicacao",""),
            "texto_original":r.get("texto_original","")[:16000]
        })
    prompt=f"""Responda à pergunta usando SOMENTE os registros abaixo da base interna do IPA.
Se houver evolução temporal, organize do mais antigo para o mais recente e destaque o estado atual.
Diferencie discussão, decisão, pendência e encaminhamento. Não invente.
Pergunta: {query}
REGISTROS:
{json.dumps(docs,ensure_ascii=False)}
"""
    url=f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    payload={"contents":[{"parts":[{"text":prompt}]}],"generationConfig":{"temperature":0.1}}
    r=requests.post(url,json=payload,timeout=60); r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"]

def show_record(r, query=""):
    title=f"{r.get('tema','Sem tema')} · {r.get('data','')}"
    with st.container(border=True):
        st.subheader(title)
        st.caption(" • ".join(r.get("comissoes",[])) + (f" · {r.get('status','')}" if r.get("status") else ""))
        if r.get("resumo"):
            st.markdown("**Resumo**")
            st.write(r.get("resumo"))
        if query:
            sn=make_snippet(r.get("texto_original") or searchable_text(r),query)
            if sn:
                st.markdown("**Trecho encontrado**")
                st.write(sn)
        c1,c2=st.columns(2)
        with c1:
            if r.get("encaminhamentos"):
                st.markdown("**Encaminhamentos**")
                st.write(r.get("encaminhamentos"))
            if r.get("pontos_pendentes"):
                st.markdown("**Pontos pendentes**")
                st.write(r.get("pontos_pendentes"))
        with c2:
            if r.get("mudancas"):
                st.markdown("**Mudanças / avanços**")
                st.write(r.get("mudancas"))
            if r.get("comunicacao"):
                st.markdown("**Comunicação**")
                st.write(r.get("comunicacao"))
        if r.get("assuntos_relacionados"):
            st.caption("Assuntos relacionados: "+", ".join(r.get("assuntos_relacionados",[])))
        original=r.get("texto_original","")
        if original:
            with st.expander("Ver conteúdo integral do paper"):
                st.text_area("Conteúdo integral",original,height=420,key=f"original_{r.get('id')}_{query[:15]}",disabled=True)
        else:
            st.caption("Este registro antigo não possui o texto integral armazenado.")

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
    st.caption("A busca consulta tema, comissão, resumo, encaminhamentos e o conteúdo integral dos papers.")
    with st.form("busca"):
        q=st.text_input("Pergunte ou pesquise",placeholder="Ex.: O que já foi discutido sobre Seguro Rural? Qual o último encaminhamento sobre crédito rural?")
        c1,c2,c3=st.columns(3)
        with c1:
            filtro_com=st.selectbox("Comissão",["Todas"]+comissoes)
        with c2:
            filtro_tema=st.selectbox("Tema",["Todos"]+existing)
        with c3:
            filtro_status=st.selectbox("Status",["Todos","Em construção","Em acompanhamento","Consolidado","Aguardando retorno","Encerrado"])
        buscar=st.form_submit_button("Pesquisar",type="primary",use_container_width=True)

    if buscar and q.strip():
        candidatos=[]
        for r in reunioes:
            if filtro_com!="Todas" and filtro_com not in r.get("comissoes",[]): continue
            if filtro_tema!="Todos" and filtro_tema!=r.get("tema"): continue
            if filtro_status!="Todos" and filtro_status!=r.get("status"): continue
            s=score_record(r,q)
            if s>0: candidatos.append((s,r))
        candidatos.sort(key=lambda x:(x[0],x[1].get("data","")),reverse=True)
        resultados=[r for _,r in candidatos]
        st.session_state["search_query"]=q
        st.session_state["search_results"]=resultados

    q2=st.session_state.get("search_query","")
    resultados=st.session_state.get("search_results",[])
    if q2:
        if not resultados:
            st.info("Nenhum conteúdo encontrado na base para essa pesquisa.")
        else:
            st.markdown(f"### {len(resultados)} registro(s) encontrado(s)")
            try:
                resposta=ai_answer(q2,resultados)
            except Exception:
                resposta=None
            if resposta:
                with st.container(border=True):
                    st.markdown("### Resposta com base nos papers")
                    st.write(resposta)
                    st.caption("A resposta acima foi produzida somente a partir dos registros encontrados na base.")
            else:
                with st.container(border=True):
                    st.markdown("### Visão rápida da base")
                    temas=sorted(set(r.get("tema","") for r in resultados if r.get("tema")))
                    datas=sorted([r.get("data","") for r in resultados if r.get("data")])
                    st.write(f"Temas relacionados: {', '.join(temas)}.")
                    if datas: st.write(f"Período encontrado: {datas[0]} a {datas[-1]}.")
                    st.caption("Quando a IA estiver configurada, esta área responderá à pergunta em texto corrido usando os papers encontrados.")
            st.divider()
            for r in resultados:
                show_record(r,q2)

elif pagina=="Temas":
    st.title("Temas")
    st.caption("Cada tema reúne o histórico de todas as reuniões e comissões relacionadas.")
    if not existing: st.info("Nenhum tema cadastrado.")
    for tema in existing:
        itens=sorted([r for r in reunioes if r.get("tema")==tema],key=lambda x:x.get("data",""),reverse=True)
        coms=sorted(set(c for r in itens for c in r.get("comissoes",[])))
        with st.expander(f"{tema} · {len(itens)} registro(s) · {len(coms)} comissão(ões)"):
            st.caption("Comissões: "+(", ".join(coms) or "—"))
            for r in itens:
                show_record(r)

elif pagina=="Comissões":
    st.title("Comissões")
    for c in comissoes:
        itens=sorted([r for r in reunioes if c in r.get("comissoes",[])],key=lambda x:x.get("data",""),reverse=True)
        temas=sorted(set(r.get("tema","") for r in itens if r.get("tema")))
        with st.expander(f"{c} · {len(temas)} tema(s) · {len(itens)} reunião(ões)"):
            if temas: st.markdown("**Temas:** "+", ".join(temas))
            else: st.caption("Nenhum tema registrado ainda.")
            for r in itens:
                st.markdown(f"**{r.get('data','')} — {r.get('tema','')}**")
                st.write(r.get("resumo",""))
                if r.get("texto_original"):
                    with st.expander(f"Ver paper integral · {r.get('data','')}"):
                        st.text_area("Texto",r.get("texto_original"),height=350,key=f"com_{c}_{r.get('id')}",disabled=True)

elif pagina=="Reuniões":
    st.title("Reuniões / Position Papers")
    st.caption("Aqui estão os registros completos que alimentam a base.")
    if reunioes:
        for r in sorted(reunioes,key=lambda x:x.get("data",""),reverse=True):
            show_record(r)
    else:
        st.info("Nenhuma reunião registrada.")

elif pagina=="Radar":
    st.title("Radar")
    c1,c2,c3=st.columns(3)
    c1.metric("Temas",len(existing))
    c2.metric("Reuniões",len(reunioes))
    c3.metric("Comissões com registros",len(set(c for r in reunioes for c in r.get("comissoes",[]))))
    demandas=[r for r in reunioes if r.get("comunicacao") and "sem demanda" not in norm(r.get("comunicacao"))]
    st.subheader("Demandas para Comunicação")
    if demandas:
        for r in sorted(demandas,key=lambda x:x.get("data",""),reverse=True):
            st.markdown(f"**{r.get('tema')} · {r.get('data')}**")
            st.write(r.get("comunicacao"))
    else:
        st.info("Nenhuma demanda registrada.")

else:
    st.title("Adicionar position paper")
    st.caption("O conteúdo integral será preservado na base. A análise serve para organizar o paper, não para substituir o original.")
    modo=st.radio("Como quer adicionar?",["Enviar arquivo","Colar texto"],horizontal=True)

    if modo=="Enviar arquivo":
        arq=st.file_uploader("PDF, DOCX ou TXT",type=["pdf","docx","txt"])
        if arq and st.button("Ler e analisar documento",type="primary"):
            try:
                texto=extract_text(arq)
                if len(texto.strip())<30:
                    st.error("Não foi possível extrair conteúdo suficiente desse arquivo.")
                else:
                    st.session_state["analise"]=analyze(texto,comissoes,existing)
                    st.session_state["texto"]=texto
                    st.session_state["origem"]="Documento"
                    st.session_state["nome"]=arq.name
            except Exception as e:
                st.error(f"Erro ao ler o documento: {e}")
    else:
        texto_colado=st.text_area("Cole aqui o position paper completo",height=360,
                                  placeholder="Cole todo o conteúdo recebido por WhatsApp, e-mail ou outro canal...")
        origem_sel=st.selectbox("Origem",["WhatsApp","E-mail","Outro"])
        st.caption(f"Caracteres capturados: {len(texto_colado):,}".replace(",","."))
        if st.button("Analisar conteúdo completo",type="primary"):
            if len(texto_colado.strip())<30:
                st.warning("Cole o conteúdo do paper antes de analisar.")
            else:
                st.session_state["analise"]=analyze(texto_colado,comissoes,existing)
                st.session_state["texto"]=texto_colado
                st.session_state["origem"]=origem_sel
                st.session_state["nome"]=""

    a=st.session_state.get("analise")
    if a:
        texto_integral=st.session_state.get("texto","")
        st.success(f"Conteúdo capturado: {len(texto_integral):,} caracteres.".replace(",","."))
        with st.expander("Conferir conteúdo integral capturado",expanded=False):
            st.text_area("Paper original",texto_integral,height=420,disabled=True)

        st.divider()
        st.subheader("Revise a classificação e a análise")
        st.caption(f"Motor: {a.get('motor','Análise local')} · Confiança na comissão: {a['conf_c']} · Confiança no tema: {a['conf_t']}")
        if a.get("tema_existente") is True:
            st.success("O tema identificado já existe na base. Este paper será acrescentado ao histórico.")
        elif a.get("tema_existente") is False:
            st.info("O sistema considera este um novo tema. Revise antes de salvar.")

        with st.form("revisao"):
            c1,c2=st.columns(2)
            with c1:
                dt=st.date_input("Data da reunião",a["data"])
                cs=st.multiselect("Comissão(ões)",comissoes,default=[x for x in a["comissoes"] if x in comissoes])
                tema=st.text_input("Tema principal",a["tema"])
            with c2:
                status=st.selectbox("Status",["Em construção","Em acompanhamento","Consolidado","Aguardando retorno","Encerrado"])
                opcoes=["Documento","WhatsApp","E-mail","Outro"]
                origem_atual=st.session_state.get("origem","Documento")
                origem_final=st.selectbox("Origem",opcoes,index=opcoes.index(origem_atual) if origem_atual in opcoes else 0)
                fonte=st.text_input("Fonte",f"Position Paper – {st.session_state.get('nome') or origem_final} – {dt.strftime('%d/%m/%Y')}")

            assuntos=st.text_input("Assuntos relacionados",", ".join(a.get("assuntos_relacionados",[])))
            resumo=st.text_area("Resumo da discussão",a["resumo"],height=220)
            enc=st.text_area("Encaminhamentos",a["encaminhamentos"],height=150)
            pend=st.text_area("Pontos pendentes",a.get("pontos_pendentes",""),height=120)
            mud=st.text_area("Mudanças / avanços identificados",a.get("mudancas",""),height=120)
            com=st.text_area("Demanda para Comunicação",a["comunicacao"],height=120)

            if st.form_submit_button("Confirmar e salvar paper completo",type="primary",use_container_width=True):
                if not cs or not tema.strip():
                    st.error("Confirme ao menos a comissão e o tema.")
                elif not texto_integral.strip():
                    st.error("O conteúdo integral do paper não foi capturado.")
                else:
                    novo={
                        "id":max([r.get("id",0) for r in reunioes],default=0)+1,
                        "data":dt.isoformat(),"comissoes":cs,"tema":tema.strip(),
                        "resumo":resumo.strip(),"encaminhamentos":enc.strip(),
                        "pontos_pendentes":pend.strip(),"mudancas":mud.strip(),
                        "assuntos_relacionados":[x.strip() for x in assuntos.split(",") if x.strip()],
                        "comunicacao":com.strip(),"status":status,"origem":origem_final,
                        "fonte":fonte.strip(),"texto_original":texto_integral,
                        "criado_em":datetime.now().isoformat(timespec="seconds")
                    }
                    reunioes.append(novo)
                    save_json(DATA_FILE,reunioes)
                    for k in ["analise","texto","origem","nome"]:
                        st.session_state.pop(k,None)
                    st.success("Paper completo registrado na base.")
                    st.rerun()
