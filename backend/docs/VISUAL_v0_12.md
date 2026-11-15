# Aether v0.12 — identidade e partículas

Pedido de18/10/2026: cores mais próximas da marca, substituir A no canto superior esquerdo pela imagem enviada e fundo em movimento inspirado na tela PS5.

## Referências usadas
Captura de tela2026-09-09 205249.png: nome/marca, fundo escuro, ciano/azul/violeta.
image(6).png: símbolo exato incorporado em data URI, bytes preservados.
image(5).png: direção de fundo com luz difusa, partículas suspensas e profundidade. Composição criada em código; não incorpora marca/textos PlayStation.

## Implementação
Canvas2D projeta coordenadas x/y/z em perspectiva. Deslocamento lento em profundidade, oscilação pequena e fade nas extremidades. Sprites de brilho pré-renderizados com gradientes radiais; partículas próximas maiores/desfocadas. 320 partículas em desktop,120 em viewport<760px, pixel ratio limitado a1.5 e alvo30fps. A fluidez real depende de navegador/hardware. CSS complementa a luz difusa com ciclo48s. Paleta central:#23d9f4,#3775ff,#a559ff. Sem pacotes extras, CDN ou dependência de internet para renderização.

Pausa cancela requestAnimationFrame; pausa ao ocultar a aba; prefers-reduced-motion mantém uma composição estática. Preferência de pausa mantida em localStorage. Canvas decorativo aria-hidden e sem captura de ponteiro. Controles continuam legíveis sobre cartões escuros.

## Validação
Chromium desktop1440×1000 e móvel390×844: símbolo carregado, captura inspecionada, ausência de overflow/erros JS, animação ativa, parada por botão, persistência da pausa após recarga e parada por movimento reduzido. Consulta longa retorna data exata do sensor, ligar e alterar cor confirmados pelo simulador. Transporte Ollama simulado; sem alegação de nova inferência real. Backend funcional v0.11 mantido, que teve80 execuções unittest aprovadas; não se apresenta esse resultado anterior como nova rodada nesta entrega visual. Instalador e integridade ZIP conferidos, banco/config preservados.

## Aceite pendente
Ryan: validar cores/logo e suavidade no Windows. Bernado: regressão visual em tamanhos distintos, pausa/movimento reduzido e comandos do painel. Não há evidência de execução por Bernado nesta entrega.
