# Contas, plano conectado e chat de voz

## Como usar

1. Abra `/conta.html` no site publicado. Escolha **Criar minha conta**.
2. Escolha usuário e senha próprios. Não é necessário convite ou senha da equipe.
3. Guarde o código de recuperação. Ele aparece uma vez e permite trocar a senha sem e-mail. Opcionalmente, confirme seu endereço para receber códigos por e-mail; veja [configuração Gmail](GMAIL_E_RECUPERACAO.md). A recuperação gera outro código e encerra as sessões anteriores.
4. Abra a Home. O plano, a maquete e o histórico pertencem à conta. Sair e entrar novamente recupera a mesma residência.
5. Em **Conversar por voz**, escolha uma voz em português do aparelho. Clique **Falar mensagem**, revise a transcrição e pressione **Enviar**. Use **Ouvir resposta** ou habilite a leitura automática.

A demonstração temporária continua acessível em `/login.html`, com dados separados. Criar conta começa uma nova residência; para trazer uma planta antiga, exporte/importa o JSON. Planos e histórico da sessão temporária não são migrados automaticamente.

## Contas e persistência

- Nomes de usuário de 3–32 caracteres, sem exigir dados pessoais ou e-mail.
- Senhas com scrypt `N=131072, r=8, p=1`, salt aleatório e limite de entrada. Hash assíncrono, até dois cálculos simultâneos por instância.
- Código de recuperação aleatório de 24 bytes; somente seu hash SHA-256 é armazenado, pois é um segredo de alta entropia, não uma senha humana.
- Sessão assinada com validade de 12 horas, cookie HttpOnly, Secure e SameSite Strict.
- Identidade da residência derivada da conta autenticada no servidor, nunca de um campo enviado pelo cliente.
- `accounts`, `auth_limits` e índices preparados automaticamente pelo cliente MongoDB.
- Limites persistidos no MongoDB: dez tentativas por nome e duzentas tentativas globais por janela de quinze minutos. Esses limites são iniciais para a demonstração e precisam ser dimensionados com medições antes de uma exposição grande.
- Recuperar senha incrementa a versão das sessões. A API verifica essa versão para impedir o uso de sessões anteriores.
- Residências de contas em `workspaces` não recebem TTL. Residências temporárias expiram em 24 horas. Cópias de plantas em `demo_projects` continuam expirando em 24 horas, inclusive nas contas.
- As credenciais MongoDB e o segredo de sessão continuam apenas no ambiente servidor do Netlify. A disponibilidade depende da configuração e das cotas do Atlas/Netlify.

A verificação de e-mail e recuperação opcional pelo Gmail estão no módulo de e-mail. MFA, console de administração e auditoria profissional de segurança não estão incluídos. Não troque a senha do usuário MongoDB com a senha dos visitantes.

## Plano e maquete

Salvar o perfil seleciona casa/apartamento, conecta a meta percentual e inclui aparelhos selecionados que ainda não existem no modelo. Não duplica aparelhos nem remove os já cadastrados. Um cômodo padrão ausente é criado ao lado dos demais, sem reposicionar os cômodos existentes; limites e sobreposições continuam validados.

O cálculo de referência usa os aparelhos e horas da maquete: potência de referência × horas/dia × 30. A Home atualiza o resumo conectado periodicamente. A referência independe do botão ligado/desligado: o indicador de potência instantânea simulada continua separado.

A conta relatada define a meta financeira, não calibra os watts dos aparelhos. Assim, R$ 200 e meta de 25% geram uma meta de R$ 50/mês; não significam economia medida. As sugestões abrangem todos os aparelhos selecionados. Não há comprovação de consumo físico ou economia real.

## Interpretação das mensagens

O classificador neural MLP permanece com os pesos existentes, acompanhado de interpretação e validação explícitas. Foram adicionadas variantes de vocabulário, pedidos com “por favor”, distinção entre “Quarto” e “Quarto 2”, remoção com confirmação e consultas de cômodos.

Negações, hipóteses, pedidos compostos e referências ambíguas não executam ações. A confirmação exige a mesma revisão da planta e expira em cinco minutos. Uma mensagem nova descarta a proposta anterior. Cada pedido possui deduplicação.

A avaliação opcional **Essa resposta ajudou?** guarda até 200 exemplos no espaço do próprio usuário. `/api/v1/assistant/feedback` permite consultar esses exemplos autenticados. São avaliações para revisão humana, não rótulos de verdade nem retreino automático. Nenhuma acurácia nova foi inventada. Conversa geral via Ollama continua disponível apenas na instalação local.

## Pesquisa de voz e decisão

| Opção | Benefício | Limite | Situação |
|---|---|---|---|
| Web Speech: síntese do navegador | Sem chave paga; vozes do sistema; leitura integral em trechos | Timbre, gênero e disponibilidade dependem do aparelho | Implementada |
| Reconhecimento nativo no aparelho | Evita enviar áudio para serviço remoto quando `processLocally` é suportado | Pacote pt-BR e compatibilidade variam | Detecção e preparo implementados |
| Reconhecimento online do navegador | Alternativa quando não há reconhecimento local | Pode enviar áudio ao provedor do navegador; depende de rede | Somente com consentimento explícito |
| Whisper no navegador com Transformers.js/WebGPU/WASM | Inferência controlada pelo aplicativo no dispositivo | Downloads de modelos, memória e desempenho precisam de testes em celulares | Pesquisado; não instalado nesta entrega |
| Whisper/Piper no Python local | Mantém a opção de instalação independente e local | Exige computador com dependências e modelos preparados | Preservado |

Não há microfone contínuo, palavra de ativação ou envio automático. O reconhecimento dura até vinte segundos, preenche o campo e permite revisão. Ao ocultar a aba ou clicar **Parar**, a escuta e a reprodução são interrompidas. Reconhecimento indisponível não bloqueia o chat por texto.

Vozes locais são o padrão. As opções de reconhecimento online e vozes online vêm desmarcadas, com aviso do possível envio de áudio/texto. Não existe fallback remoto silencioso. A permissão do microfone só é solicitada após o clique do usuário. O Aether não armazena gravações nesse modo; o texto enviado ao chat permanece no histórico da conta.

A Web Speech API não padroniza o gênero de uma voz. A lista mostra nomes reais disponíveis e origem local/online, sem prometer uma voz feminina ou masculina específica. Velocidade de leitura 0,94; todos os trechos do plano podem ser lidos, sem descartar a segunda sugestão.

### Fontes primárias consultadas

- MDN, SpeechRecognition: https://developer.mozilla.org/en-US/docs/Web/API/SpeechRecognition
- MDN, reconhecimento no aparelho: https://developer.mozilla.org/en-US/docs/Web/API/SpeechRecognition/available_static
- MDN, vozes disponíveis: https://developer.mozilla.org/en-US/docs/Web/API/SpeechSynthesis/getVoices
- Hugging Face, Whisper/WebGPU: https://huggingface.co/docs/transformers.js/guides/webgpu
- OWASP, armazenamento de senhas: https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html

## Validação e limites

Os testes usam MongoDB simulado e DOM simulado para verificar: conta persistente entre logins, isolamento, recuperação de código, invalidação de sessão antiga, confirmação do chat, sincronização de horas/aparelhos, consentimento remoto, transcrição sem envio e leitura integral das respostas.

Esses testes não substituem escuta real em Android/iPhone ou validação do banco em produção. O cadastro é aberto, com limites de tentativas. Use `cd site && npm ci && npm run check`.
