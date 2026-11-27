# E-mail do Aether pelo Gmail

## O que está implementado

- Cadastro e confirmação do e-mail em **Conta → E-mail de recuperação**.
- Código de seis dígitos para confirmar endereço e recuperar senha.
- Código válido por dez minutos, uso único, até cinco tentativas por desafio.
- Recuperar senha gera um novo código de recuperação offline e invalida as sessões antigas.
- Mensagem personalizada com o plano completo, incluindo todas as sugestões. O destinatário é sempre o endereço confirmado da própria conta.
- Preferência de consentimento para mensagens personalizadas. O envio do plano ocorre quando solicitado, não há newsletter automática.
- Modelo de mensagem com identidade Aether, HTML escapado e versão texto.
- O cadastro sem convite, a senha e o código de recuperação offline continuam funcionando sem SMTP.

A credencial do Gmail ainda precisa ser configurada no ambiente do servidor antes de qualquer envio real. Código implementado e testes simulados não comprovam que uma mensagem chegou à caixa de entrada.

## Configurar no Netlify

Em **Project configuration → Environment variables**, adicione com escopo de Functions/produção:

| Variável | Valor |
|---|---|
| `GMAIL_USER` | Endereço completo do Gmail remetente escolhido pela equipe |
| `GMAIL_APP_PASSWORD` | Senha de aplicativo de 16 caracteres gerada pelo Google para essa conta |

A senha de aplicativo deve ficar marcada como secreta no Netlify. Não use a senha normal do Gmail. Não salve a credencial no GitHub, em variáveis públicas, arquivos de frontend ou neste documento. Publique novamente após alterar as variáveis.

O Gmail precisa permitir senhas de aplicativo e ter verificação em duas etapas. Algumas contas de organizações, com proteção avançada ou políticas específicas, não oferecem essa opção. Consulte a página oficial: https://support.google.com/mail/answer/185833

A aplicação usa o transporte Gmail do Nodemailer, com TLS e limites de espera. O remetente usa o endereço autenticado, sem aceitar outro remetente enviado pelo navegador. Não há anexos nem leitura de arquivos/URLs pelo transporte.

### Alternativa OAuth

Se já possuir uma integração Google Cloud autorizada para SMTP, o código também aceita `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` e `GOOGLE_REFRESH_TOKEN`, além de `GMAIL_USER`. Quando os três existem, OAuth tem prioridade. Essa credencial SMTP precisa de autorização adequada; uma conexão do plugin Gmail do ChatGPT não é automaticamente uma credencial do backend Netlify.

A documentação do Nodemailer recomenda OAuth para novas integrações e aceita senha de aplicativo quando a verificação em duas etapas já está disponível: https://nodemailer.com/guides/using-gmail

## Como o visitante usa

1. Cria ou acessa sua conta.
2. Abre **Conta → E-mail de recuperação**, informa seu endereço e solicita o código.
3. Digita os seis dígitos recebidos e confirma o endereço.
4. Se desejar, autoriza mensagens personalizadas.
5. Na Home, clica **Receber este plano por e-mail**.

Se esquecer a senha, abre **Conta → Esqueci a senha: receber código por e-mail**, informa o nome de usuário, recebe o código e define a nova senha. Depois guarda o novo código offline.

Não existe recuperação por e-mail para contas que nunca confirmaram um endereço. Nesses casos, use o código offline do cadastro.

## Proteções

- Endereços só são habilitados para recuperação após prova de acesso à caixa de entrada.
- O código não é retornado pela API; apenas enviado pela mensagem. O MongoDB guarda HMAC com segredo do servidor, não o código em texto puro.
- A expiração é validada pela API, independentemente da limpeza TTL em `mail_challenges`.
- O desafio é consumido atomicamente e vinculado ao usuário, à versão da sessão e ao e-mail. Código antigo não recupera uma conta cujo endereço confirmado já mudou.
- As solicitações públicas não revelam o endereço cadastrado e retornam a mesma mensagem para usuário desconhecido ou sem e-mail confirmado. Não há garantia de tempo de resposta constante: um envio SMTP pode demorar mais.
- Limites iniciais: três solicitações por usuário/endereço em quinze minutos, três envios de plano por conta em quinze minutos e duzentas mensagens gerais por dia no aplicativo. O Google possui cotas próprias e pode bloquear envios antes desse limite.
- Não há endpoint para escolher destinatários arbitrários, envio em massa ou mensagens livres.
- A preferência de mensagens personalizadas pode ser desativada na conta. Códigos de segurança solicitados pelo usuário permanecem disponíveis.

## Verificação

Após cadastrar as variáveis e publicar:

1. Entre em uma conta permanente e confirme que a seção de e-mail está ativada.
2. Solicite confirmação para uma caixa de entrada da equipe, confira inbox/spam e valide o código.
3. Teste recuperação, código expirado, código reutilizado e envio do plano.
4. Confirme que sair e entrar exige a nova senha após recuperação.

Os testes automatizados usam remetente simulado: validam confirmação, consentimento, recuperação, expiração e uso único sem gastar cota ou enviar mensagens a terceiros. Uma resposta `sent` significa que o Gmail aceitou a mensagem para entrega, não que ela foi lida ou recebida fora do spam.

Para uma exposição grande, dimensione cotas e entregabilidade antes de divulgar: o Gmail pessoal é adequado a uma demonstração pequena, não substitui um provedor transacional de grande volume.
