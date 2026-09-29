# IPA – Construção de Temas | MVP 0.4

Aplicação em Streamlit para organizar a memória das comissões do IPA por **comissão → tema → reuniões/position papers**.

## Funcionalidades atuais
- 12 comissões do IPA pré-cadastradas;
- temas podem se relacionar a uma ou mais comissões;
- envio de PDF, DOCX e TXT;
- opção de colar diretamente textos recebidos por WhatsApp, e-mail ou outro canal;
- leitura assistida de data, comissão, tema, resumo, encaminhamentos e demanda para Comunicação;
- revisão humana antes de salvar;
- pesquisa na base e visualização de temas, comissões, reuniões e radar.

## Executar
```bash
pip install -r requirements.txt
streamlit run app.py
```

A próxima etapa é conectar uma camada de IA para interpretação semântica, identificação de temas já existentes e respostas sobre a evolução histórica dos assuntos.
