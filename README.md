# IPA – Construção de Temas | v0.7

Versão com base limpa, visual reformulado e foco em:

- armazenamento do conteúdo integral dos papers;
- pesquisa em tema, comissão, resumo, encaminhamentos e texto completo;
- visual mais moderno, sóbrio e alinhado às cores do IPA;
- comissões oficiais pré-cadastradas;
- cadastro por upload ou colagem de texto.

## Observações

- `data/reunioes.json` foi zerado para receber apenas papers reais.
- A camada de IA continua opcional via `st.secrets` com `GEMINI_API_KEY` e `GEMINI_MODEL`.
- Próxima evolução recomendada: persistência em banco (Supabase).

## Execução local

```bash
pip install -r requirements.txt
streamlit run app.py
```
