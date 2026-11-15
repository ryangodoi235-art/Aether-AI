# Aether AI 0.14-RC2 — pacote consolidado para homologação

Esta versão reúne o sistema local e o painel Netlify. RC2 significa candidata a liberação: o pacote não comprova que microfone, voz, hospedagem e equipamentos físicos já funcionam no seu ambiente.

## Começar no Windows
1. Extraia o ZIP em uma pasta NOVA. Não sobrescreva o projeto antigo nem apague seu banco.
2. Entre em backend. Essa é a raiz do projeto Python, onde estão requirements.txt e os arquivos BAT.
3. Tenha Python e Ollama instalados. A regressão desta entrega usa Python 3.12/Linux. Outras versões/Windows precisam de validação na instalação.
4. Execute PREPARAR_TUDO.bat. Ele instala a aplicação, baixa qwen2.5:3b e prepara Whisper/Piper. Há downloads de vários GB. O teste final sintetiza uma frase e verifica sua transcrição. Não usa seu microfone nem aciona dispositivos.
5. Execute INICIAR_COMPLETO.bat e mantenha a janela aberta. Ele reutiliza o Ollama ou inicia um processo próprio. Abra http://127.0.0.1:8000/painel.
6. Execute DIAGNOSTICAR.bat em outra janela. Envie diagnostico_aether.json se algo falhar.
7. Faça o roteiro de aceite abaixo. Só depois publique para a equipe.

O painel mantém as cores, logo e fundo do Aether. A resposta falada automática permanece ativa por padrão. O navegador pode exigir um primeiro clique para liberar áudio. A gravação preenche o texto para revisão antes de enviar.

## Aceite do teste completo
- Ligar/desligar luz-sala e tomada-sala e verificar estado após recarregar.
- Ligar luz-quarto, pedir vermelho e brilho 40%. Conferir resultado.
- Pedir brilho 101% e uma ação incompatível. Nenhum sucesso falso.
- Consultar a última temperatura e seu horário. Não confundir com o dataset de 2010.
- Criar uma rotina, executar e conferir cada ação e histórico.
- Criar um cômodo/dispositivo simulado, reiniciar e conferir persistência.
- Fazer pergunta aberta à IA com Ollama ligado. Depois testar indisponibilidade sem resposta inventada.
- Executar TESTAR_VOZ.bat. Depois falar no microfone, revisar o texto, enviar e ouvir a resposta automática no navegador.
- Validar em outro navegador/celular e registrar ambiente, versão, resultado e evidência.
- Quando online: senha errada não pode acessar dados nem comandos. Sair deve exigir nova entrada. Testar outra rede e voz remota.

Use backend/RELATO_TESTE.md para registrar falhas. Bloqueio não equivale a teste aprovado.

## Netlify e backend remoto
A pasta site contém o painel e a função de conexão. Importar pelo Git ou usar CLI com Functions. Publicar somente HTML por arrastar e soltar não basta.
Base directory: site (se o repositório tiver este pacote inteiro). Publish directory: public. Functions: netlify/functions. Sem build command. Node 22 ou superior.

Configure no Netlify, com escopo para Functions:
- AETHER_API_URL: origem HTTPS do servidor Python, sem caminho /api.
- AETHER_API_TOKEN: segredo de pelo menos 32 caracteres, igual ao configurado no backend.
- AETHER_TEST_PASSWORD: senha de teste com pelo menos 12 caracteres. Use uma senha aleatória longa para compartilhar apenas com a equipe.
- AETHER_SESSION_SECRET: segredo aleatório diferente, de pelo menos 32 caracteres. Não compartilhe com os testadores.

Gere segredos individualmente no PowerShell: python -c "import secrets; print(secrets.token_urlsafe(48))"
Não envie os segredos no chat, não grave no HTML e não publique no Git. Repita o deploy depois de configurar.

O servidor remoto deve executar backend.app.cloud:app, HTTPS externo, uma única instância/worker e armazenamento persistente para /app/data e /app/config. O diretório config precisa conter house.json do pacote. main:app é apenas para localhost e NÃO aplica a proteção por token da entrada cloud.

AETHER_OLLAMA_URL permite apontar para o serviço Ollama interno. O padrão é http://127.0.0.1:11434. Dentro de Docker, localhost é o contêiner. Prepare os modelos de voz também no servidor. O Dockerfile básico ainda não traz modelos/pesos de IA ou voz. O Netlify não executa o Ollama no computador do visitante.

O gateway aceita corpos de até 3 MB e aguarda até 50 segundos. Aqueça os modelos antes de testar. Se um comando expirar, consulte o estado antes de reenviar.

A senha libera uma sessão de 12 horas. Cookie HttpOnly, Secure e SameSite=Strict. O botão Sair limpa a sessão do navegador. Para revogar todas as sessões, altere AETHER_SESSION_SECRET e faça novo deploy. É uma senha compartilhada de testes, não contas individuais ou isolamento de dados. A casa e o histórico são compartilhados. Não há bloqueio persistente por tentativas de senha nesta versão. Não use como produto público ou com dispositivos reais conectados ao link.

## O que ainda depende de validação externa
Voz real no PC, qualidade do áudio, publicação HTTPS, teste em outra rede e equipamento físico. A voz personalizada JARVIS/XTTS permanece fora desta candidata, pois não teve execução confirmada. Piper é a voz padrão.
Integração Home Assistant existente exige endereço, token e mapeamento de entidades do equipamento. Não existe garantia universal para qualquer marca/modelo. Previsões históricas e estimativas de consumo não representam economia real comprovada. Aprendizado automático de preferências e compatibilidade universal continuam objetivos futuros, não funções concluídas.

## Preservar a instalação anterior
O pacote inicia uma casa fictícia limpa. Para continuar dados antigos: pare o servidor antigo, faça uma cópia integral dele e só então copie config/house.json e data/aether.sqlite3 para os mesmos locais dentro de backend da nova versão. Não copie .venv. Modelos podem ser reaproveitados copiando models. A nova versão cria tabelas/colunas ausentes; mantenha a cópia antiga para retorno. Migração com seu banco real ainda exige validação.
