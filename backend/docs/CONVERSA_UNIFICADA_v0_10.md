# Conversa unificada v0.10 — entrega e validação

Campo único para comandos do simulador e perguntas. Mantidos logo, paleta e fundo CSS 3D. Campo separado de comandos removido; botões dos dispositivos e endpoint /api/v1/text preservados.

## Contrato de confirmação
O backend executa comandos reconhecidos e só confirma após retorno do simulador. Snapshot é coletado após a ação. Cor com luz desligada exige ligar primeiro; não há ação implícita. Nomes ambíguos ou ausentes pedem identificação. Pedidos negativos e compostos não são executados parcialmente.

API de conversa retorna answer, status, actions_executed, command, context, request_id, response_source e notice. Repetição com mesmo ID/texto recupera resposta; mesmo ID/texto diferente retorna 409. Caso estado mude depois, reenvio continua devolvendo o resultado histórico original: use o painel para consultar estado atual.

## Evidência desta entrega
76 execuções unittest aprovadas em Python/Linux: regressão da API, sensores, histórico, automação, previsão, conversa, validação, comandos e reenvio após reinício. Transporte Ollama simulado nos testes; nenhuma alegação de nova inferência real no computador de Ryan. Modelo real qwen2.5:3b foi validado anteriormente por Ryan em teste isolado.

## Aceite no Windows — Ryan e Bernado
Seguir exemplos de LEIA_PRIMEIRO.md; registrar versão, entrada, resultado e captura/JSON. Verificar cartão e histórico após cada comando, persistência após reinício, comando com Ollama fechado, pergunta aberta com erro de indisponibilidade, brilho 101%, cor em luz sem suporte, dispositivo indisponível, ambiguidade, negação e pedido composto. Não marcar como aprovado um caso bloqueado. Comparar previsão histórica com registro salvo, sem tratar como consumo atual. Testar layout em janela estreita e pausa do fundo.

RY-06 e RY-05 permanecem em progresso até conferência local. Bernado executa regressão quando receber esta versão; nenhuma execução dele foi presumida. Escala de contexto, memória, voz e hardware real são etapas futuras.

## Conferência complementar
Chromium headless: desktop 1440×1000 e celular 390×844, capturas inspecionadas. API local real e transporte Ollama simulado. Comandos ligar/cor vermelha/brilho40%, ambiguidade, pergunta aberta, atualização de cartões e recarga aprovados; sem erros JavaScript ou transbordamento horizontal móvel. Instalador executado em cópia de teste preservou os hashes de config/house.json e data/aether.sqlite3. Conferência final com Ollama real no Windows permanece pendente.
