# Validação 0.14-RC2 — 05/11/2026

99 testes unittest aprovados em 10,789 segundos, Python 3.12/Linux. Cobrem API, comandos, persistência, sensores, rotinas, catálogo, energia, previsões e fluxo de voz com motores simulados. Três novos testes distinguem diretório Whisper vazio, arquivos presentes e rejeição por ausência dos modelos.

Gateway Node: suíte aprovada para senha correta/incorreta, cookie assinado/adulterado, origem de escrita, configuração de backend, corpo excessivo, transporte de áudio, erro HTTP e indisponibilidade. Entrada cloud verificada com token ausente/incorreto e correto. Sintaxe Python e JavaScript verificada.

A primeira regressão apontou a necessidade de atualizar o fixture de voz: o antigo teste criava apenas um diretório vazio. O fixture agora inclui arquivos simulados requeridos pela checagem, mantendo o motor de teste explícito. Resultado final acima após a correção.

Não executados aqui: inferência real Piper/Whisper/Ollama, microfone ou áudio de navegador, scripts BAT no Windows, build Docker, deploy Netlify e integração com equipamento físico. TESTAR_VOZ.bat realiza a inferência real no computador após instalar modelos. A sessão online usa senha compartilhada e não substitui autenticação individual de produção.

Documentação Netlify consultada para roteamento e limite de função: https://docs.netlify.com/build/functions/configuration/ . Gateway de 50s fica abaixo do limite síncrono documentado de 60s; corpo de 3MB mantém margem para binários.
