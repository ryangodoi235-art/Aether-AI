# Interface e próximos passos do Aether

## Entregue nesta atualização

O tema da publicação Netlify foi unificado em `site/public/experience.css`, compartilhado pela Home, maquete e plano. O build aplica esse tema sem substituir os arquivos da instalação Python.

- Fundo azul escuro, contraste consistente, destaque verde-água e violeta secundário.
- Sidebar menor, navegação horizontal no celular e botões com altura mínima de 44 px.
- Maquete em toda a largura, área 3D maior, controles ao lado no desktop e abaixo no celular.
- Chat e plano lado a lado em telas largas, empilhados em telas menores.
- Exemplos de comandos apenas preenchem a mensagem: nunca executam ações sem envio.
- Estado vazio do chat e aviso de conexão real com a API; falhas de autenticação/banco permanecem visíveis.
- Avisos de sessão integrados ao conteúdo, sem faixa fixa sobre os controles.
- Link para cópias de plantas dentro da navegação, sem botão flutuante sobre a maquete.
- Animação decorativa pausada por padrão. O limite de resolução e a renderização sob demanda já existentes na maquete foram preservados.
- Consultas de sensores pausadas em abas ocultas; leituras sem alteração de estado não geram atualizações MongoDB.

## Pesquisa e critérios

A W3C diferencia alvos mínimos de 24 px e a recomendação ampliada de 44 px. Os botões desta atualização usam altura mínima de 44 px; isso não constitui auditoria completa de conformidade WCAG.

Fonte: https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum/

O manual oficial do Three.js explica o custo adicional de renderizar todos os pixels em telas de alta densidade. A implementação atual já limita o pixel ratio a 1,25 e renderiza sob demanda, por isso não foi substituída por um loop contínuo.

Fonte: https://threejs.org/manual/pages/responsive.html

## Melhorias recomendadas, ainda não implementadas

| Prioridade | Melhoria | Critério de conclusão |
|---|---|---|
| 1 | Concluir validação Netlify–Atlas | Login correto, consulta, gravação e leitura após recarregar testados em produção |
| 1 | Contas individuais permanentes | Recuperar a própria planta após novo login, com testes de isolamento entre usuários |
| 1 | Jornada inicial curta | Moradia, moradores e conta em poucos passos; teste com visitantes sem ajuda da equipe |
| 1 | Mensurar o entendimento do chat | Dataset de frases reais, separado por intenção e família; precisão e cobertura publicadas |
| 2 | Sincronizar plano e aparelhos 3D | Uma única configuração para potência e horas, refletida em gráficos e sugestões |
| 2 | Undo e histórico de alterações | Restaurar exclusões e explicar exatamente o que mudou |
| 2 | Desempenho em aparelhos reais | Testes em Android, iPhone e notebook; medir carregamento, FPS e requisições |
| 2 | Sessão de demonstração isolada | Reavaliar a liberação ampla de rede do Atlas após a exposição, sem remover acesso durante a demonstração |
| 3 | Conversão de plantas PDF | Escala confirmada pelo usuário; revisão de paredes, cômodos e medidas antes da importação |
| 3 | Voz na versão online | Definir solução compatível com processamento e privacidade; não anunciar Ollama/Piper como executados no Netlify |

## Validação realizada

`cd site && npm ci && npm run check`: build e oito testes automatizados. Os testes cobrem os contratos existentes, isolamento, CAS, deduplicação, equivalência neural, confirmação de chat, cálculo de meta e ausência de escrita em leituras imutáveis. `node --check site/public/experience.js` valida sintaxe.

A tentativa de avaliação visual automatizada ficou bloqueada: o Chromium local não está completo e o download do navegador de teste foi recusado pela rede. Portanto, esta entrega não afirma validação visual em celulares reais nem auditoria completa de acessibilidade. A conexão real com Atlas também precisa de login válido no site, cuja última tentativa foi rejeitada.
