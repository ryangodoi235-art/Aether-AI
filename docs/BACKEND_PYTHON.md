# Backend Python do Aether

O servidor FastAPI já inclui maquete, controles RGB, sensores simulados, plano de economia e redes neurais MLP. Esta entrega prepara a execução protegida para o Netlify, sem API paga de inteligência artificial.

**Preparar código não cria automaticamente um servidor hospedado.** É necessário executar o backend no seu notebook/servidor ou criar um serviço de hospedagem. Só depois existe uma URL para cadastrar no Netlify.

## Recursos e limites

| Recurso | Backend preparado |
| --- | --- |
| Casa/apartamento, cômodos e aparelhos | API existente e persistência SQLite |
| Ligar/desligar, brilho e RGB | Operações validadas nos aparelhos compatíveis |
| Sensores | Simulação explícita, sem sensores físicos |
| Plano de economia | Perfil e projeções aritméticas; não garante economia |
| Chat neural | Classificador MLP local; comandos continuam sujeitos a revisão/validação |
| Conversa aberta | Ollama opcional, no mesmo servidor; não está incluído na imagem leve |
| PDF e DXF | Dependências incluídas para os adaptadores existentes; conversão de PDF continua experimental |
| Voz e microfone | Exigem modelos e pacotes adicionais; não ficam prontos automaticamente |
| MongoDB | A função do Netlify guarda cópias JSON; este backend mantém SQLite |
| Vários visitantes | Residência de demonstração compartilhada, sem isolamento por conta |

## Opção A — notebook Ubuntu, com dados locais

Na raiz do repositório atualizado:

```bash
git pull --ff-only
bash PREPARAR_BACKEND_UBUNTU.sh
bash INICIAR_BACKEND_UBUNTU.sh
```

Se outro Aether já estiver usando a porta 8000, encerre-o com Ctrl+C no terminal correspondente. Não execute dois servidores na mesma porta.

O preparo cria um ambiente separado em `backend/.venv-cloud` e um token aleatório em `.env.backend`, com permissão de arquivo restrita. Repetir o preparo preserva o token existente. Não publique esse arquivo nem envie seu conteúdo ao chat.

O script local habilita a integração opcional com Ollama; mantenha o Ollama e o modelo baixado se desejar conversa aberta. Para usar apenas a MLP, altere `AETHER_GENERAL_LLM=0` em `.env.backend`.

Se o ambiente antigo já contém suas vozes e modelos preparados, você pode utilizá-lo explicitamente:

```bash
AETHER_BACKEND_PYTHON=./backend/.venv-ubuntu/bin/python bash INICIAR_BACKEND_UBUNTU.sh
```

O servidor escuta apenas em `127.0.0.1`. Para conectá-lo ao Netlify é necessário um proxy/túnel **HTTPS público**, mantendo o notebook ligado. O endereço `http://127.0.0.1:8000` não funciona no Netlify. Não exponha a porta do Ollama. A URL do proxy deve apontar para esse backend protegido, não para o antigo `main:app` sem token.

Verifique o processo local:

```bash
curl --fail http://127.0.0.1:8000/healthz
```

O resultado `status: ok` comprova apenas que a API responde. Não comprova voz, Ollama ou medições reais.

## Opção B — Docker no seu servidor

Após preparar `.env.backend`, execute na raiz:

```bash
docker compose -f compose.backend.yaml up --build -d
docker compose -f compose.backend.yaml logs -f api
```

A porta fica restrita a localhost e os dados ficam no volume `aether-data`. Configure um proxy HTTPS no servidor. Não use `down --volumes` se quiser preservar o SQLite.

A imagem leve não instala Ollama, Whisper ou as vozes. O arquivo Compose utiliza as configurações do `.env.backend`; desative `AETHER_GENERAL_LLM` quando não houver um Ollama alcançável pelo processo. Um Ollama no host não é o localhost do container; essa ligação depende da sua implantação.

## Opção C — demonstração hospedada no Render

O arquivo `render.yaml` na raiz descreve um Web Service Docker no plano `free`. Não cria disco pago nem serviço de IA. Na conta Render, crie um Blueprint a partir deste repositório e revise o plano antes de publicar.

Para cadastrar o serviço manualmente:

| Campo | Valor |
| --- | --- |
| Repositório | `ryangodoi235-art/Aether-AI` |
| Branch | `main` |
| Runtime | Docker |
| Dockerfile Path | `backend/Dockerfile.cloud` |
| Docker Build Context | `backend` |
| Health Check Path | `/healthz` |
| Instância | Free, para demonstração |

O Blueprint solicita a geração de `AETHER_API_TOKEN`. No cadastro manual, defina um token aleatório de pelo menos 32 caracteres. Use o mesmo valor no Netlify, sem colocá-lo no repositório. O comando `serve_cloud.py` usa a porta fornecida pela hospedagem e apenas um worker.

**Limites do plano gratuito:** o serviço pode dormir quando ocioso, demorar a acordar e perder arquivos locais após reinício/deploy. Portanto o SQLite dessa modalidade é descartável. Não use esse modo como armazenamento definitivo nem prometa persistência da casa dos visitantes. A migração completa da aplicação para MongoDB não faz parte desta entrega.

Para preservar os dados, prefira a opção local com volume persistente ou planeje armazenamento durável separadamente. Não é necessário contratar um plano para testar o backend.

Na hospedagem leve, `AETHER_GENERAL_LLM=0`: o chat usa a MLP e explicita seus limites. Não haverá uma IA generativa geral nem voz pronta apenas por subir o container.

## Conectar ao Netlify

Depois que a API tiver uma URL HTTPS real:

1. Abra as variáveis do projeto `aether-ai-ryan` no Netlify.
2. Cadastre `AETHER_API_URL` com a origem HTTPS do backend, sem caminho ou credenciais.
3. Cadastre `AETHER_API_TOKEN` com o mesmo token do servidor, marcado como segredo.
4. Faça um novo deploy do site.

Não use a senha `AETHER_TEST_PASSWORD` como token. Ela protege o login dos visitantes; `AETHER_API_TOKEN` protege a comunicação entre Netlify e Python.

O gateway encaminha o token em `X-Aether-Token`. Todas as rotas do backend, inclusive documentação e páginas, exigem esse header; apenas `/healthz` é público. Os visitantes acessam a interface pelo Netlify, e não diretamente pela URL Python.

## Configurações do servidor

| Variável | Uso |
| --- | --- |
| `AETHER_API_TOKEN` | Obrigatório: 32–512 caracteres ASCII, sem espaços |
| `PORT` | Porta HTTP; padrão 8000 |
| `AETHER_DATA_DIR` | Diretório do SQLite e do cadastro persistente |
| `AETHER_CONFIG_PATH` | Caminho opcional do cadastro, quando houver configuração própria |
| `AETHER_LOCAL_NLU` | Habilita a MLP; padrão 1 |
| `AETHER_GENERAL_LLM` | 1 permite Ollama opcional; 0 mantém o modo leve |
| `AETHER_LOCAL_TIMEOUT` | Limite da chamada Ollama; padrão 40 s nesta entrada |

O arquivo `house.json` é inicializado no diretório de dados apenas quando ainda não existe. Reiniciar o servidor não substitui o catálogo editado. O gateway do Netlify aguarda até 50 segundos; chamadas mais lentas podem falhar, especialmente ao acordar uma hospedagem gratuita.

## Verificação

```bash
cd backend
.venv-cloud/bin/python -m pip install -r requirements-dev.txt
.venv-cloud/bin/python -m unittest discover -s tests -p test_cloud_backend.py -v
```

Os testes exercitam autenticação, rejeição de token inválido, maquete e repetição idempotente, persistência após recriar a aplicação, sensores simulados, perfil de energia e chat MLP sem rede. O teste local não comprova publicação em uma conta de hospedagem.

Após publicar, confira `/healthz` e, pelo gateway do Netlify, `/api/v1/deployment/status`, `/api/v1/maquette`, `/api/v1/maquette/sensors` e `/api/v1/assistant/status`. Teste voz separadamente apenas após preparar os modelos.

Fontes: https://render.com/docs/deploy-fastapi e https://render.com/docs/free
