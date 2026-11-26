# Aether no Netlify com MongoDB

## Escopo desta integração

O Netlify entrega a interface atual do Aether e executa uma função Node.js como ponte para a API Python. O MongoDB armazena **cópias JSON dos projetos**, acessíveis pelo botão “Cópias no MongoDB” na Home. O banco SQLite local não foi removido nem migrado.

As cópias do MongoDB pertencem à sessão autenticada, não a contas permanentes. Elas expiram em 24 horas e deixam de ser acessíveis ao encerrar/expirar a sessão de 12 horas, trocar de navegador ou renovar o segredo de sessão. Baixe o JSON antes de sair. Não use este modo como armazenamento definitivo.

O servidor Python continua com uma residência de testes compartilhada. O isolamento das cópias não transforma o restante da aplicação em um sistema multiusuário. Cadastros individuais, recuperação de conta e isolamento da maquete/chat exigem uma próxima implementação.

## Arquitetura

1. Navegador → Netlify: interface e sessão de testes.
2. Netlify Function → MongoDB: cópias temporárias dos arquivos JSON.
3. Netlify Function → backend HTTPS: maquete, chat, sensores simulados e demais APIs existentes.
4. Backend → Ollama/voz local: recursos opcionais do computador anfitrião.

Netlify e MongoDB Atlas são serviços na nuvem. Esta modalidade **não é totalmente local**. O funcionamento local existente continua separado. O Netlify não consegue acessar `127.0.0.1` do notebook; a API precisa de um endereço HTTPS alcançável pelo serviço. O modelo Ollama permanece no anfitrião e não deve ter sua porta exposta publicamente.

## 1. MongoDB

Use uma instância MongoDB alcançável pelas funções, como um cluster Atlas. Crie um usuário de banco restrito à base `aether`, com permissões para documentos e criação dos índices. Configure a política de acesso de rede de acordo com o ambiente de implantação. Não publique a URI, a senha ou o arquivo `.env` no GitHub.

No painel do Netlify, configure `MONGODB_URI` e `MONGODB_DB=aether` como variáveis do servidor. A conexão reutiliza um pool limitado; cria índices de proprietário/data e expiração TTL. O TTL limpa documentos em segundo plano, mas a API bloqueia imediatamente os documentos cuja validade já acabou.

## 2. Backend Python

No servidor que executará o Aether, crie um `AETHER_API_TOKEN` aleatório com pelo menos 32 caracteres. Instale os requisitos da versão local e execute, dentro de `backend`:

```bash
.venv-ubuntu/bin/python -m uvicorn backend.app.cloud:app --host 127.0.0.1 --port 8000
```

Disponibilize essa aplicação atrás de um proxy/túnel HTTPS com suporte à sua rede. O serviço deve permanecer ligado. Use o mesmo token no backend e no Netlify. Não coloque o token no HTML e não utilize o módulo `main:app` desprotegido como API pública.

O gateway atual limita cargas/respostas a 3 MB e aguarda até 50 segundos. Conversas locais lentas podem exceder esse prazo; antes de repetir um comando após erro, confira o estado. Voz, modelos neurais e dependências de PDF devem ser preparados nesse servidor, como na instalação local.

## 3. Publicar no Netlify

Importe o repositório `ryangodoi235-art/Aether-AI`, branch `main`. O arquivo `netlify.toml` da raiz define:

| Campo | Valor |
| --- | --- |
| Base directory | `site` |
| Build command | `npm run build` |
| Publish directory | `site/dist` relativo ao repositório, ou `dist` relativo à base |
| Functions directory | `site/netlify/functions` relativo ao repositório |
| Node | 22 |

O build copia `backend/frontend` para a publicação. Evita publicar somente a antiga interface de `site/public`. Não é necessário carregar ambientes Python nem pesos de modelos para o Netlify.

Configure estas variáveis no painel, disponíveis para as Functions, e faça um novo deploy:

| Variável | Finalidade |
| --- | --- |
| `MONGODB_URI` | Conexão privada com o banco |
| `MONGODB_DB` | Nome da base; padrão `aether` |
| `AETHER_TEST_PASSWORD` | Senha de testes com pelo menos 12 caracteres |
| `AETHER_SESSION_SECRET` | Segredo aleatório com pelo menos 32 caracteres |
| `AETHER_API_URL` | Origem HTTPS do backend, sem caminho |
| `AETHER_API_TOKEN` | Mesmo token configurado no backend |

O exemplo sem credenciais está em `site/.env.example`. `localhost`, `127.0.0.1` e endereços privados sem conectividade externa não servem como backend para as funções do Netlify. O MongoDB sozinho não substitui o servidor Python.

## 4. Conferir a publicação

1. Abra `/login.html`, autentique e acesse `/painel`.
2. Confirme que a maquete carrega pelo gateway.
3. Exporte um JSON da planta pelo Aether.
4. Abra “Cópias no MongoDB”, envie o arquivo e baixe a cópia salva.
5. Abra uma sessão anônima separada e confira que essa cópia não aparece.
6. Exclua a cópia na sessão original.
7. Teste chat e voz separadamente; dependem do backend e dos modelos locais.

MongoDB não configurado retorna 503 sem revelar credenciais. Uma sessão expirada retorna 401. Erro 502 nas demais APIs indica falha de acesso ou demora do servidor Python.

## Verificação automatizada

```bash
cd site
npm ci
npm run check
```

Os testes de banco usam armazenamento substituto para verificar isolamento, validação, expiração, exclusão e tratamento de falhas. Eles não comprovam conexão com um cluster real. A validação ponta a ponta requer as contas e variáveis reais do ambiente de publicação.

Fontes oficiais: https://docs.netlify.com/build/functions/environment-variables/ e https://www.mongodb.com/docs/drivers/node/current/connect/connection-options/connection-pools/
