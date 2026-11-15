# Aether — testes internos 0.13.3-RC1

Pacote completo para uma instalação nova. Não é atualização do banco de Ryan. Extraia em uma pasta própria, por exemplo C:\Aether_Testes, sem substituir o projeto existente. Cada testador terá sua casa simulada e seu banco. Não inclui dados pessoais, tokens, modelos de fala, Ollama ou a referência de voz do filme. Não é publicação na internet.

## Começar

1. Tenha Python64bits disponível no comando `python`. O código foi verificado em Python3.12/Linux; a instalação e aceitação no Windows devem ser registradas pelo testador. Ryan usa Python3.14. Se uma dependência falhar, registre a versão e o erro, sem alterar versões por tentativa.
2. Abra INSTALAR.bat e aguarde “Instalacao concluida”. Instala API, fusos e previsão histórica.
3. Abra INICIAR.bat. Deixe o terminal aberto e acesse http://127.0.0.1:8000/painel.
4. Confira “TESTES INTERNOS · 0.13.3-RC1” na conversa. Use Ctrl+F5 se necessário. Mantenha apenas uma instância na porta8000; pare o Aether antigo antes.
5. Comece pelos cenários de texto em ROTEIRO_TESTES.md. Não exigem microfone nem Ollama, exceto a explicação aberta.

## IA local opcional

Instale/abra Ollama no PC do testador. Execute `ollama pull qwen2.5:3b` uma vez e confira `ollama list`. Se o servidor não estiver aberto, execute `ollama serve` em outro terminal. Recarregue o painel. O download inicial usa internet; o modelo roda localmente.

## Voz padrão opcional

Execute PREPARAR_VOZ.bat uma vez com internet para instalar Whisper/Piper e baixar os modelos. Reinicie o Aether. Permita o microfone para127.0.0.1; grave, revise e envie. Aether pode falar novas respostas automaticamente. A preferência pode ser desligada em Preferências de voz; Parar áudio interrompe a reprodução. Se o navegador bloquear reprodução automática, use Ouvir resposta e registre o caso.

Voz de referência/XTTS: BLOQUEADA e excluída desta rodada. Ryan relatou que ainda não funciona. Não instalar Coqui nem executar os scripts de referência neste pacote. A voz padrão validada anteriormente por Ryan é diferente dessa opção experimental.

## Limites desta rodada

- Casa simulada; confirmação não significa equipamento físico acionado.
- Previsão de2010 é demonstração histórica, nunca consumo atual. Valores novos dependem da janela selecionada.
- Energia manual é identificada como não verificada. Hardware real e Home Assistant estão fora do aceite desta rodada.
- Agenda exige PC/servidor abertos, um processo, fuso America/Sao_Paulo; não repõe horários perdidos.
- O banco começa sem histórico. Sensores sem amostra devem informar ausência; registre uma amostra simulada antes de comparar a consulta.
- Consultas factuais reconhecidas usam estados do backend. Explicações abertas por IA podem conter erros e devem ser avaliadas.

## Encaminhar resultados

Bernado pode executar o roteiro; Ryan centraliza correções. Participação e início devem ser confirmados pela equipe. Preencha RELATO_TESTE.md com versão, cenário, entrada, esperado, observado, resultado e evidência. Não envie tokens ou dados pessoais. Evite vários relatórios para o mesmo erro; registre a frequência.

Na triagem: impeditivo = não instala/inicia, perde dados, executa ação incorreta ou confirma ação não executada; importante = funcionalidade principal falha com alternativa; visual = apresentação sem bloquear uso. Falha ou bloqueio não conta como aprovado. Esta é uma candidata de teste, não uma versão final validada pela equipe.
