# Roteiro — 0.13.3-RC1

Execute em ordem e registre um resultado por cenário. Comece numa instalação nova. Para persistência, reinicie o servidor sem apagar data/config. Registre simulação em todas as evidências desta rodada.

| ID | Fazer | Esperado |
|---|---|---|
| T01 | Instalar, iniciar, abrir painel | Sem traceback; versão correta, sala/quarto/dispositivos carregados |
| T02 | “Ligue a luz do quarto”; depois “Desligue a luz do quarto” | Estado e histórico correspondem a cada comando |
| T03 | Ligar quarto; “Deixe a luz do quarto vermelha”; “Defina o brilho da luz do quarto para 40%” | Cor RGB255,0,0 e brilho40; conferir no painel/API |
| T04 | Pedir brilho101%; pedir brilho na luz da sala | Rejeita; nenhum sucesso falso nem mudança indevida |
| T05 | “Ligue a luz” → “A do quarto”; repetir ambiguidade → “cancelar” | Esclarecimento resolve só o quarto; cancelar não aciona |
| T06 | “Não ligue a luz da sala” e dispositivo inexistente | Nenhuma execução indevida |
| T07 | Registrar temperatura simulada pelo painel; perguntar última temperatura e horário | Valor e timestamp iguais à amostra; sem inventar data ou monitoramento contínuo |
| T08 | “Quais dispositivos estão ligados na casa?” | Lista bate com cadastro/estado; não inclui sensor como atuador ligado |
| T09 | Adicionar cômodo e luz simulada no Cadastro | Novo dispositivo aparece e aceita ligar/desligar |
| T10 | Criar rotina de desligar luzes simuladas; executar | Etapas e estado confirmados; histórico visível |
| T11 | Agendar rotina para2min à frente, fusoSãoPaulo, servidor aberto | Executa uma vez no horário; conferir registro |
| T12 | Reiniciar servidor | Cadastro, estados e histórico permanecem |
| T13 | Gerar previsão com janela de demonstração | Origem histórica e intervalo explícitos; sem chamar de consumo atual |
| T14 | Registrar três leituras manuais cumulativas em horários distintos | Diferença emkWh correta; origem manual não verificada e estimativa identificadas |
| T15 | Com Ollama: “Explique o objetivo do Aether” | Resposta em português; não afirma executar ação inexistente |
| T16 | Com voz preparada: gravar pergunta, revisar, enviar, ouvir; testar silêncio/parar | Texto reconhecido, resposta falada e controles funcionam; gravação sozinha não executa |
| T17 | Fechar Ollama e testar comando simples e explicação aberta | Comando determinístico funciona; explicação informa indisponibilidade |
| T18 | Janela estreita, navegar por teclado, pausar fundo e recarregar | Sem controles inacessíveis/rolagem lateral; foco visível e pausa preservada |

T15–T17 podem ficar bloqueados por pré-requisitos, com motivo registrado. Não conte bloqueio como sucesso. Testes de voz de referência e hardware físico não fazem parte desta liberação. Para T14, use um medidor com ID teste-equipe e horários reais distintos, sem alterar registros existentes.
