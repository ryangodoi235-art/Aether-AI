# Identidade Aether AI

## Nova marca

O símbolo combina a letra A, telhado de residência, folha com raio de energia e conexões de uma rede neural. A marca usa ciano/verde-água e violeta, sobre azul-marinho. O nome **Aether AI** permanece como texto HTML para continuar legível e acessível.

Arquivo: `site/public/brand/aether-symbol.png`. PNG com transparência, gerado para o projeto. O original anterior não foi apagado da instalação Python. A implementação desta atualização é aplicada ao build online do Netlify.

### Brief utilizado na criação

Uma única marca, sem palavras na imagem; casa inteligente e letra A integradas; folha/raio para energia e economia; três conexões neurais; geometria simples, fundo transparente e cores próximas de `#71e4d5`, `#a999ff` e `#080e1c`. Uso previsto: cabeçalho, navegação e ícone de aba.

## Onde aparece

Home, conta, acesso temporário, cópias de plantas, maquete independente, plano e laboratório neural recebem a identidade. Os iframes não repetem o cabeçalho completo da página principal. O favicon usa o mesmo símbolo.

Os novos elementos de navegação representam recursos existentes, não novas promessas: residência 3D, plano de economia, chat com voz e laboratório neural. Sensores continuam simulados.

## Computador e celular

- Desktop: identidade na navegação lateral, quatro cartões de acesso e área principal larga.
- Tablet: cartões em duas colunas e adaptação do espaço disponível.
- Celular: atalhos inferiores Casa, Chat, Plano e Conta; sem segundo chat. Botões respeitam a área segura do aparelho.
- Campos de texto e seletores com fonte mínima de 16 px no celular; foco de teclado visível.
- Maquete e editor empilham em telas estreitas. A área 3D adapta a altura também em orientação horizontal.
- Rótulos de consentimento de voz têm área de toque ampliada. Os dados e credenciais não mudam com o tema.

## Carregamento

O build substitui as duas imagens antigas embutidas em base64 pela referência ao arquivo da marca. A Home gerada caiu de aproximadamente 3,49 MB para 54 KB de HTML, antes da transferência HTTP. O PNG separado ocupa aproximadamente 670 KB e é reutilizado. Esses valores não representam o tamanho total do aplicativo ou uma medição de velocidade em 4G.

## Verificação

Build e testes verificam referências aos arquivos, existência dos destinos de navegação, preservação dos formulários e ausência das imagens antigas embutidas na Home publicada. A inspeção em celulares físicos e testes completos de acessibilidade continuam necessários antes da apresentação.
