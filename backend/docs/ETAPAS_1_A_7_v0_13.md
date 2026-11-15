# Aether v0.13 — contrato, ativação e validação

##1 — Consultas confiáveis
Perguntas de dispositivos reconhecidas são respondidas por regras usando o cadastro completo e estados consultados, inclusive em casas maiores: listas ligadas/desligadas/disponíveis, estado singular, brilho e RGB. Exemplos:
- Quais dispositivos estão ligados na casa?
- Quais luzes estão desligadas na sala?
- A tomada da sala está ligada?
- Qual é o brilho da luz do quarto?
- Qual é a cor da luz do quarto?

Ausência de capacidade, estado desconhecido, cômodo inexistente e ambiguidade são informados. Temperatura continua com timestamp UTC integral. Perguntas sobre dados não reconhecidas pedem reformulação em vez de gerar um valor. Perguntas abertas explicativas ainda usam qwen2.5:3b e podem conter erros.

Explicações abertas para contexto>7000 caracteres passam a receber um resumo limitado com aviso explícito de quantidade incluída/total. Consultas por regras continuam percorrendo o cadastro inteiro. O cadastro admite até500 cômodos e5000 dispositivos como limite de validação; isso não é promessa de desempenho nem de compatibilidade com qualquer tamanho. Teste automatizado de escala incluiu253 dispositivos simulados. Muitas entidades físicas exigem consultas de rede e podem demorar.

##2 — Contexto por sessão
O painel envia session_id persistente neste navegador. Uma ambiguidade de comando guarda apenas a ação/valores e candidatos, por5 minutos. “A do quarto”, nome completo ou ID resolve unicamente dentro desses candidatos; estado/capacidades são revalidados. “cancelar” limpa a pendência. Outro pedido independente limpa/substitui a pendência. Não há memória geral de todos os diálogos nem resolução livre de pronomes.

Clientes API devem enviar session_id único. O valor padrão default é para compatibilidade com scripts de um usuário e não isola clientes diferentes. request_id igual/texto/sessão iguais recupera resposta; mudança de texto/sessão retorna409. Histórico anterior e comandos permanecem preservados. Sessão é contexto de uso local, não autenticação multiusuário.

##3 — Rotinas e horários
PUT /api/v1/routines/{id}: id,name,actions,enabled,time(HH:MM opcional),timezone. No painel, o construtor monta ações e permite editar/excluir rotinas. Suportados ligar/desligar, brilho e RGB conforme capacidades. Execução manual/por chat registra cada etapa e usa IDs estáveis para evitar reenvio duplicado. Pré-validação rejeita campos/ações inválidos. Falha durante execução interrompe as próximas etapas; ações anteriores não são desfeitas. Status partial deve ser revisado.

Agendador local consulta a cada10 segundos e executa uma vez por rotina/data no fuso configurado. Horários passados com servidor fechado não são repostos. Use um processo e mantenha o computador ligado. Em queda durante uma rotina, histórico running não significa sucesso e não é retomado automaticamente; confira os dispositivos. Horários usam tzdata no Windows, instalado por requirements-features.txt. O teste do agendador verifica instantes explícitos e repetição no mesmo dia; não substitui teste prolongado no PC.

A regra térmica herdada continua exclusiva do simulador e é rejeitada para dispositivos físicos. Rotinas já podem usar comandos físicos. Automação térmica contínua de hardware não foi implementada.

##4 — Cadastro pelo painel
GET/PUT /api/v1/catalog com revision evita sobrescrever uma edição antiga. Pode adicionar/editar nomes, cômodos, disponibilidade e capacidades. IDs existentes, tipo/origem/entidade física são duráveis: para mudar integração use outro dispositivo e desative o anterior; exclusão de dispositivos com histórico foi evitada. Dispositivo novo simulado começa desligado; editar initial_state não substitui o estado corrente.

Arquivo é salvo com substituição atômica e cópia before-edit, e os novos estados são adicionados sem limpar histórico. Resolução e filtros são gerados pelo cadastro. O UI atualiza por recarga após salvar; cadastro é local e não exige LLM.

##5 — Voz local
preparar_voz.py instala faster-whisper,piper-tts,huggingface_hub e baixa Systran/faster-whisper-tiny e pt_BR-faber-medium. A instalação depende de pacotes binários compatíveis com seu Python/Windows; microfone e saída de áudio precisam ser testados localmente. Voz é opcional e ausência não impede texto.

POST /api/v1/voice/transcribe recebe áudio bruto, limitado a8MB e30s decodificados. Whisper usa CPU int8/4 threads, português e local_files_only. Áudio temporário é removido. Não é um serviço com timeout de inferência rígido; uma transcrição pode demorar em CPU. POST /api/v1/voice/speak recebe text até1500 caracteres, chama Piper local e retorna WAV temporário. Download somente durante preparação explícita. Modelos podem ser apontados por AETHER_WHISPER_MODEL e AETHER_PIPER_MODEL. Gravação preenche o campo, exige revisão/Enviar e não aciona dispositivos sozinha.

Licenças: bibliotecas/modelos continuam sob suas próprias licenças (Piper GPL; verificar os modelos/voz antes de redistribuir/comercializar). O ZIP não inclui pesos.

##6 — Home Assistant local
Pré-requisito externo: Home Assistant local operante e equipamentos integrados nele. Aether usa a API REST oficial, Bearer token do usuário e leitura de estado; não cria uma ponte automaticamente no equipamento.

No PowerShell que iniciará o Aether:

```powershell
$env:AETHER_HA_URL = "http://192.168.1.100:8123"
$env:AETHER_HA_TOKEN = "SEU_TOKEN_LOCAL"
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Troque IP/token pelo seu servidor. Não envie seu token para a conversa. Configure via cadastro origem Home Assistant e entidade conforme tipo: light.quarto, switch.tomada_sala, sensor.temperatura_sala ou sensor.energia_casa. Capacidades cadastradas precisam corresponder às do equipamento; a ponte não detecta toda compatibilidade automaticamente. RGB só é confirmado por comparação com rgb_color retornado; equipamentos que reportam outra representação podem ficar não confirmados.

Verificar conexão não aciona equipamentos. Comando físico usa /api/services/{domain}/{service} e consulta /api/states/{entity}; apenas sucesso observado é confirmado. Falha/timeout não é substituída por simulação. Ação enviada sem confirmação pode ter ocorrido fisicamente: atualize/inspecione antes de usar outro ID. Reenvio do mesmo ID recupera o resultado salvo, sem nova chamada ao serviço. Isso não promete exatamente uma execução no hardware em quedas de energia/rede. Estados físicos são consultados sob demanda; não há MQTT/WebSocket/polling contínuo.

Sincronizar leitura grava temperatura em°C ou energia cumulativa emkWh; W não é energia. UI identifica fonte física/simulada. A URL é configurada no ambiente e limitada a endereço de rede local, sem proxy/redirecionamentos. A API Aether permanece em127.0.0.1, sem autenticação multiusuário para exposição em rede.

##7 — Energia medida e estimativa
Manual: POST /api/v1/energy/readings com request_id,meter_id,timestamp com fuso,cumulative_kwh. Fonte manual_unverified. Automática sob demanda: POST /api/v1/hardware/sync/{id} em medidor físico cadastrado, unidade kWh, fonte home_assistant. Leituras duplicadas não são inseridas novamente. Medidor cumulativo não pode diminuir; use outro ID após reset/troca.

GET /api/v1/energy/summary?meter_id=... exige3 amostras. Calcula diferença cumulativa, janela e consumo médio por hora, extrapolando uma hora após a última leitura. Informa origem, amostras e se última leitura tem até15min. Usa no máximo100 amostras recentes. Não é potência instantânea, nem previsão UCI, nem modelo treinado/validado na casa. Não há promessa de economia. Precisamos coletar dados reais e avaliar erro em divisão temporal antes de promover a estimativa a previsão validada. Arquitetura de medições pronta não equivale a teste com seu medidor.

## Validação desta entrega
96 execuções unittest aprovadas em Python3.12/Linux: regressão anterior, consultas sem modelo, sessão isolada/expiração/reinício/reenvio, cadastro/revisão/persistência, rotinas/pré-validação/parcial/agendamento/idempotência, energia/monotonicidade/unidade/origem, falha de hardware e verificação de estado, voz ausente/limites e fluxo com mecanismos simulados. Teste de escala em253 dispositivos. Voz, Home Assistant e Ollama usaram mecanismos/respostas de teste; nenhum equipamento/microfone de Ryan foi acessado.

Chromium desktop1440×1000/mobile390×844: conversa com esclarecimento, fatos, construtor/executar rotina, cadastro real de cômodo com recarga, dados de energia no painel, estados de voz/hardware não preparados, sem overflow/erro JS; capturas inspecionadas. Instalador e preservação de banco/config verificados em cópia.

## Roteiro de aceite — Ryan/Bernado
F01 consultas/valores/indisponíveis; F02 esclarecer/cancelar/expirar/duas sessões; F03 rotina e horário real no Windows/servidor fechado/falha parcial; F04 cadastro novo/edição/revisão/conflito/reinício; F05 preparar modelos/gravar/transcrever/revisar/ouvir sem internet; F06 configurar ponte e testar equipamento físico com falha/readback; F07 medidor real/unidade kWh/amostras/reset/estimativa. Enviar versão, entrada, esperado, observado e evidência em04 Testes. Bloqueios externos não contam aprovados. Execução por Bernado não presumida.

## Fontes técnicas consultadas
- https://developers.home-assistant.io/docs/api/rest/
- https://github.com/SYSTRAN/faster-whisper
- https://github.com/OHF-Voice/piper1-gpl/blob/main/src/piper/download_voices.py
- https://github.com/OHF-Voice/piper1-gpl/blob/main/src/piper/__main__.py
- https://huggingface.co/rhasspy/piper-voices/tree/main/pt/pt_BR/faber/medium
