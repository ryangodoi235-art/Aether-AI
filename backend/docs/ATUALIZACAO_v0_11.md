# Aether v0.11 — temperatura e ambiente visual

## Problema observado
Em 17/10/2026 o modelo respondeu 26.5°C em 2010-04-22T21:49:11, enquanto a consulta direta devolveu 26.5°C em 2026-10-07T21:49:11.322119+00:00. O erro de data foi comprovado pelas respostas enviadas por Ryan. A causa interna da geração não foi estabelecida; a data de 2010 também existe no contexto histórico de energia.

## Correção
O interpretador agora reconhece a frase longa “Qual foi a última temperatura registrada na sala e em que horário?” e variantes com última/registrada/medida, na/no e pedido de horário. Usa o mesmo cadastro e consulta do endpoint direto; resposta inclui o timestamp UTC integral, com precisão e fuso preservados. Não faz conversão de fuso pelo modelo. Nomes de cômodos e sensores continuam resolvidos pelo cadastro; nenhum valor/data da evidência foi fixado no produto.

Ambiguidade, cômodo inexistente, sensor indisponível e ausência de amostra produzem resposta explícita. Outras frases com temperatura recebem orientação controlada para reformular e não são enviadas ao modelo. Não há monitoramento contínuo: as amostras desta versão são registradas manualmente no simulador. Prompt aether-local-v4 reforça essa distinção; perguntas abertas fora das regras ainda podem ter erros. Histórico preservado, com aviso nos textos gerados por versões anteriores.

## Fundo
Substituídos cubo, órbitas e grade por camadas translúcidas curvas, luz difusa e profundidade em perspectiva, em ciano/azul/violeta. Movimento pequeno e contínuo de 36–60 segundos, sem reação ao mouse ou flashes. SVG e CSS locais, sem rede/bibliotecas gráficas extras. Mantidos pausa persistida, pausa com aba oculta e respeito à preferência de movimento reduzido; em telas menores a composição e a difusão são ajustadas.

## Validação
80 execuções unittest aprovadas em Python/Linux. Incluem reprodução da data exata do defeito, variantes de frase, ausência de leitura, sensor indisponível, cômodo desconhecido, múltiplos sensores e garantia de que essas consultas não chamam o modelo. Testes anteriores de comandos, sensores, persistência, automação e inferência histórica também passaram. Transporte Ollama simulado; inferência real desta versão no Windows ainda depende da conferência de Ryan.

## Roteiro Bernado
Repetir pergunta longa e curta e comparar texto/valor/timestamp com GET /api/v1/sensors/{id}/reading; conferir ausência de amostra, sensor indisponível e duas salas/sensores sem seleção indevida. Confirmar que histórico antigo continua visível com aviso. Testar ligar/cor/brilho pelo chat, fundo em desktop/celular, pausa com recarga e movimento reduzido. Registrar versão, entrada, esperado/observado e evidências em 04 Testes. Execução de Bernado não presumida.

## Limites mantidos
Somente simulação. Sem voz/hardware real/memória conversacional. Perguntas abertas têm limite de contexto de7000 caracteres; ampliação para casas maiores ainda pendente. Comandos resolvem o cadastro completo e não dependem desse limite do modelo. Não há aceitação automática de sugestões do modelo.

## Conferência da interface e instalador
Chromium headless1440×1000 e390×844, com API real e transporte Ollama simulado. Capturas inspecionadas: fundo e leitura dos cartões, consulta longa com timestamp exato, comandos ligar/vermelho, animações lentas ativas, pausa persistida após recarga, redução de movimento e ausência de overflow móvel/erros JavaScript. Instalador testado em cópia: hashes de banco/config preservados. Suavidade no hardware de Ryan e inferência real do modelo nesta versão ainda pendentes.
