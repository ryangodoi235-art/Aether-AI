# Aether: Netlify Functions + MongoDB

A demonstração online usa Functions Node.js e MongoDB diretamente. **Não precisa de Render, servidor Python, AETHER_API_URL ou AETHER_API_TOKEN.** A instalação Python local permanece independente, com seus recursos e SQLite.

## Funcionalidades desta etapa

| Recurso | Demonstração online |
|---|---|
| Casa/apartamento, cômodos e aparelhos | Maquete persistida por conta ou sessão temporária; inclusão, remoção e edição pelos controles |
| Luz RGB e brilho | Apenas luzes compatíveis; estado persistido |
| Sensores | Temperatura, umidade, presença, potência e energia fictícias; cálculo sob demanda |
| Plano de economia | Conta relatada, moradores, meta, dicas para todos os aparelhos selecionados; sem garantia de economia |
| Chat | MLP de intenção existente + validação por regras; propostas exigem `confirmar ação`; não é conversa livre |
| Redes neurais | Mesmos pesos do Python, inferência JavaScript de intenções e previsão sintética; testes de equivalência |
| Plantas | Importação/exportação JSON; PDF/DXF/OpenPlan continuam na versão local |
| Dispositivos antigos | Consulta e controles básicos de ligar/desligar/RGB/brilho |
| Voz, Whisper, Ollama, Home Assistant | Whisper/Ollama/Piper/Home Assistant na versão local; voz do navegador disponível no painel de voz |
| Cadastros legados, rotinas, automações contínuas | Não migrados; seções extras omitidas da publicação online |

O perfil conecta os aparelhos selecionados e a meta à maquete. A referência de consumo usa as horas da maquete; a meta financeira da conta relatada continua separada. Veja [contas, plano e voz](CONTAS_PLANO_E_VOZ.md).

## Configuração no Netlify

Repositório `ryangodoi235-art/Aether-AI`, branch `main`. A raiz `netlify.toml` define base `site`, build `npm run build`, publicação `dist` e Functions `netlify/functions`. Node 22 ou superior.

Variáveis de servidor necessárias:

- `MONGODB_URI`: URI do usuário de banco Atlas, com senha correta e caracteres especiais codificados na URI.
- `MONGODB_DB`: `aether`.
- `AETHER_TEST_PASSWORD`: opcional, apenas para a demonstração temporária; mínimo 12 caracteres quando definida.
- `AETHER_SESSION_SECRET`: segredo aleatório de pelo menos 32 caracteres.

Não coloque valores secretos no GitHub, HTML, prefixos públicos ou capturas de tela. As funções precisam alcançar o cluster: configure as regras de rede do Atlas conforme o ambiente. O usuário do banco precisa ler/escrever a base e criar índices. Após mudar variáveis, publique novamente.

O modo antigo de proxy Python é opcional: somente `AETHER_BACKEND_MODE=python` ativa esse caminho, que exige as variáveis antigas e backend HTTPS. Deixe essa variável ausente para o modo recomendado.

## Privacidade, duração e concorrência

O cookie assinado dura 12 horas e usa HttpOnly, Secure e SameSite Strict. Em `/conta.html`, usuário e senha dão acesso à mesma residência após novo login. A senha usa scrypt e a recuperação usa um código aleatório de uso único. O proprietário é verificado pelo servidor. Consulte o guia de contas para os limites de tentativas e cuidados com o código de recuperação.

Residências de contas permanentes não recebem expiração TTL. A demonstração temporária em `/login.html` mantém expiração de 24 horas, e suas sessões são independentes. As cópias JSON em `demo_projects` expiram em 24 horas em ambos os modos. O estado é armazenado como JSON; nomes dos usuários não viram operadores MongoDB. Não há fallback de dados em memória quando o banco falha.

A gravação usa versão e comparação atômica (CAS), com nova tentativa em conflitos. Revisões da maquete impedem aplicar um comando sobre uma planta alterada. Os últimos 32 identificadores de solicitação guardam o resultado para evitar repetição; o chat confirma somente propostas ainda atuais e dentro de cinco minutos. Histórico limitado às últimas 60 mensagens. Limite de 1 MB por entrada JSON e 4 MB de estado por sessão.

## Verificação

```bash
cd site
npm ci
npm run check
```

Os testes usam um banco simulado com CAS, não comprovam conectividade com seu Atlas. Cobrem isolamento, concorrência, deduplicação, confirmação obsoleta, RGB, sensores, plano e equivalência numérica com o Python.

Após entrar no site, `/api/v1/database/status` deve retornar `status: ready`. Se retornar `DB_AUTH_FAILED`, revise usuário/senha da URI; `DB_CONFIG_MISSING` indica configuração ausente; `DB_UNAVAILABLE` exige conferir rede e disponibilidade do cluster. A resposta nunca revela a URI.

Netlify e Atlas são serviços em nuvem: essa demonstração **não é totalmente local**. Custos e cotas dos provedores continuam aplicáveis. Nenhum modelo LLM ou sintetizador de voz pesado é carregado nas Functions.
