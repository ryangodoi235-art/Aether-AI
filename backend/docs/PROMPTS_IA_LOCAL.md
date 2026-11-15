# Aether local — promptv5/versão0.13

Modelo explicativo qwen2.5:3b. Texto SYSTEM em backend/app/assistant_service.py. Consultas reconhecidas de temperatura, estados, brilho, RGB e disponibilidade são respondidas diretamente pelo backend. Dados variam por origem simulation/home_assistant. Nenhuma ferramenta é dada ao modelo.

Contexto de esclarecimento tem sessão e expira em5min; não é memória geral do modelo. Perguntas explicativas grandes recebem resumo explícito e contagem incluída/total. O histórico mantém pergunta/resposta/contexto/origem/modelo/prompt_version/session_id. Cached request_id é vinculado ao texto e à sessão. Respostas antigas não são corrigidas retroativamente.

Energia histórica permanece controlada; medições da casa e baseline têm fluxo próprio. Voz transcreve antes do envio e usa a mesma API de conversa. Roteamento/limites/ativação/testes documentados em ETAPAS_1_A_7_v0_13.md.
