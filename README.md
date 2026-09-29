# IPA – Construção de Temas

MVP 0.2 de uma aplicação para organizar, pesquisar e acompanhar a evolução dos temas discutidos nas comissões do IPA.

## Estrutura de informação

A aplicação separa três entidades principais:

- **Comissão**: estrutura fixa do IPA;
- **Tema**: assunto acompanhado ao longo do tempo e que pode aparecer em mais de uma comissão;
- **Reunião / Position Paper**: registro datado que alimenta o histórico do tema.

## Comissões pré-cadastradas

- Alimentação e Saúde
- Ambiental
- Bioenergia
- Conselho Jurídico
- Defesa Animal
- Defesa Vegetal
- Direito de Propriedade
- Infraestrutura e Logística
- Política Agrícola
- Relações Internacionais
- Trabalhista
- Tributária

## Rodar localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

## MVP 0.2

- Home com a chamada **“Qual assunto você quer pesquisar hoje?”**;
- página de Temas;
- nova página de Comissões;
- comissões oficiais pré-cadastradas;
- página de Reuniões;
- Radar;
- cadastro de novos registros;
- base local em JSON para prototipação.

## Próximas etapas

1. upload de PDF/DOCX;
2. identificação automática da comissão e do tema;
3. criação automática de novos temas, preservando as comissões fixas;
4. sugestão de vínculo com tema já existente;
5. leitura por IA e extração de resumo, encaminhamentos e demandas de Comunicação;
6. banco Supabase;
7. respostas com histórico e fontes;
8. relatório consolidado por tema;
9. autenticação de usuários.
