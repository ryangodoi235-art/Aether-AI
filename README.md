# Aether AI — Inteligência para economizar

**Protótipo acadêmico de assistência residencial e planejamento de economia de energia, com execução local.**

O Aether AI ajuda moradores a compreender o consumo estimado dos aparelhos, explorar uma residência interativa em 3D e planejar mudanças de hábitos. A proposta é transformar informações de energia em uma experiência visual e acessível, com apoio de inteligência artificial.

> **Para a avaliação:** a residência e os sensores demonstrados são simulados. Os valores de consumo e economia são estimativas; não representam medições físicas comprovadas nem garantem redução da conta.

## O que o projeto oferece

| Recurso | Aplicação |
| --- | --- |
| Residência interativa | Representação de casa ou apartamento, com cômodos e aparelhos editáveis. |
| Maquete 3D | Visualização dos ambientes e dos estados dos dispositivos. |
| Controle de aparelhos | Ações de ligar e desligar; brilho e RGB nos dispositivos compatíveis. |
| Sensores simulados | Leituras fictícias para demonstrar a apresentação de informações ambientais e energéticas. |
| Chat integrado | Interpretação de solicitações relacionadas à residência e aos aparelhos. |
| Plano de economia | Simulação de metas, sugestões de hábitos e projeções financeiras. |
| Inteligência artificial local | Classificação neural de intenções e experimento de previsão de consumo; integração opcional com Ollama. |
| Voz local opcional | Síntese de fala e reconhecimento de voz, mediante instalação dos pacotes e modelos necessários. |
| Plantas e arquivos | Módulos de importação, exportação e integração experimental com plantas e openPlan. |

A maquete serve como uma residência de exemplo. Sua configuração pode ser modificada pelo usuário, mas não deve ser interpretada como levantamento arquitetônico certificado.

## Como a inteligência artificial é utilizada

O projeto combina modelos aprendidos com regras de validação. Cada parte tem uma função:

| Componente | Responsabilidade |
| --- | --- |
| Rede neural MLP de intenções | Classificar pedidos, como adicionar um aparelho, criar um cômodo ou alterar um estado. |
| Rede neural MLP de energia | Experimentar previsão de consumo com dados sintéticos. |
| Qwen 2.5 via Ollama — opcional | Apoiar a interpretação e a conversa em linguagem natural, executando no computador local. |
| Backend em Python | Validar dispositivos, cômodos, parâmetros e capacidades antes de aplicar alterações. |
| Cálculos de consumo | Estimar energia e custo a partir da potência, do tempo de uso e da tarifa informados. |

**Não se trata apenas de uma coleção de respostas prontas:** há modelos neurais com pesos armazenados no projeto. Entretanto, regras continuam necessárias para validar comandos e apresentar resultados de forma controlada.

O Qwen é um modelo previamente treinado por terceiros. Configurar instruções para ele não equivale a treinar ou fazer fine-tuning do modelo.

### Avaliação dos modelos

As métricas estão disponíveis em [metrics.json](backend/backend/app/neural_models/metrics.json). O classificador de intenções registra aproximadamente **72,3% de acurácia no conjunto de teste sintético**.

Esse resultado descreve o experimento registrado, não uma garantia de compreensão de qualquer frase. A avaliação sintética também não comprova desempenho em residências reais. O laboratório neural pode ser acessado em **/neural** com o servidor iniciado.

## Como a economia é estimada

Para um aparelho com potência e tempo de uso definidos:

```text
Consumo em kWh = (potência em W / 1.000) × horas de uso por dia × dias
Custo estimado = consumo em kWh × tarifa informada
```

Esse cálculo é distinto da previsão realizada pelo modelo neural.

Por exemplo, uma conta de **R$ 650,00** com meta de redução de **25%** corresponde a uma meta de **R$ 487,50**, ou **R$ 162,50 por mês** de economia pretendida. Mantida por doze meses, essa diferença seria de **R$ 1.950,00**.

Trata-se de uma projeção matemática. O resultado efetivo depende dos hábitos, dos aparelhos, da tarifa e das condições da residência. A conta real também pode incluir cobranças não representadas na simulação.

## Arquitetura e execução local

- **Interface:** HTML, CSS e JavaScript, com visualização 3D baseada em Three.js/Blueprint3D.
- **Backend:** Python e FastAPI.
- **Persistência:** SQLite.
- **IA:** modelos MLP locais e integração opcional com Ollama.
- **Áudio:** módulos locais opcionais de síntese e transcrição.

No modo iniciado por `INICIAR_UBUNTU.sh`, o sistema utiliza o inicializador neural local, sem exigir chaves Fish Audio ou OpenAI.

A instalação de dependências e o download inicial de modelos podem precisar de internet. Para uso sem conexão, os modelos, pacotes e demais recursos necessários devem estar previamente disponíveis no computador.

**Local não significa individual por visitante:** a execução atual no computador anfitrião não deve ser considerada uma solução pronta de isolamento de dados entre múltiplos usuários.

## Executar no Ubuntu

É necessário ter Python com suporte a ambientes virtuais. O ambiente utilizado no desenvolvimento em Ubuntu usa Python 3.12.

Na pasta em que deseja baixar o projeto:

```bash
git clone https://github.com/ryangodoi235-art/Aether-AI.git
cd Aether-AI

python3 -m venv backend/.venv-ubuntu
backend/.venv-ubuntu/bin/python -m pip install --upgrade pip
backend/.venv-ubuntu/bin/python -m pip install -r backend/requirements.txt

bash ./INICIAR_UBUNTU.sh
```

Acesse **http://127.0.0.1:8000/painel**. Mantenha o terminal aberto; use **Ctrl+C** para encerrar.

As dependências básicas iniciam a aplicação. Voz, transcrição, previsão histórica e processamento de plantas possuem dependências e/ou modelos adicionais.

### Conversa com Ollama — opcional

Com o Ollama instalado e em execução no mesmo computador:

```bash
ollama pull qwen2.5:3b
```

O endereço padrão é `http://127.0.0.1:11434`. A velocidade das respostas depende do hardware, da carga do modelo e do tamanho do contexto.

### Voz — opcional

O projeto contém suporte a vozes locais feminina e masculina e a transcrição local. Esses recursos exigem preparação específica; não ficam disponíveis apenas com a instalação de `backend/requirements.txt`.

Consulte [preparar_duas_vozes.py](preparar_duas_vozes.py), [local_voices.py](backend/backend/app/local_voices.py) e [voice.py](backend/backend/app/voice.py). A compatibilidade dos pacotes e a geração de áudio devem ser verificadas no ambiente da demonstração.

## Roteiro sugerido para os avaliadores

1. Abra a Home e explore a residência de exemplo.
2. Configure cômodos e aparelhos.
3. Altere estados na maquete e experimente RGB em uma luz compatível.
4. Observe as leituras identificadas como simuladas.
5. Informe uma conta aproximada e uma meta de economia.
6. Compare as projeções e as sugestões apresentadas.
7. Experimente o chat e revise os pedidos de confirmação quando apresentados.
8. Abra **/neural** para consultar os recursos neurais.

A documentação interativa da API está em **http://127.0.0.1:8000/docs**.

## Plantas e integração 3D: limites atuais

A integração com openPlan é experimental e utiliza adaptação/troca de arquivos. Não equivale a substituir automaticamente toda a maquete por outro editor.

O processamento de PDF depende das características da planta e pode exigir ajuste de escala e revisão manual. **Não há garantia de conversão automática de qualquer PDF em uma residência 3D completa**, com móveis e medidas corretos. Os módulos correspondentes estão em [openplan_adapter.py](backend/backend/app/openplan_adapter.py), [openplan_routes.py](backend/backend/app/openplan_routes.py) e [pdf_rooms.py](backend/backend/app/pdf_rooms.py).

## Organização do código

| Local | Conteúdo |
| --- | --- |
| `backend/backend/app/` | API, chat, maquete, sensores e integrações. |
| `backend/backend/app/neural_models/` | Artefatos e métricas dos modelos neurais. |
| `backend/backend/app/ml/` | Inferência e adaptador da demonstração histórica de consumo. |
| `backend/frontend/` | Interface e recursos visuais. |
| `backend/config/` | Configuração da residência. |
| `backend/tests/` | Testes automatizados. |

Para executar os testes existentes, a partir da raiz:

```bash
cd backend
.venv-ubuntu/bin/python -m pip install -r requirements-dev.txt
.venv-ubuntu/bin/python -m unittest discover -s tests
```

## Limitações e próximos passos

- Validar o projeto com sensores físicos e medições reais.
- Ampliar os dados de treinamento e avaliar linguagem natural com usuários.
- Melhorar a importação de plantas e a fidelidade da maquete.
- Validar usabilidade, acessibilidade e desempenho em diferentes dispositivos.
- Implementar e testar isolamento de dados para acesso simultâneo de visitantes.

O repositório também preserva módulos de versões anteriores e integrações opcionais. A presença desses arquivos não significa que todos estejam ativos no inicializador local.

## Equipe

**Ryan, João, Reinaldo, Davi e Bernardo**  
Gestão da Tecnologia da Informação — **GTI-4-noite**

Projeto acadêmico voltado à aplicação de inteligência artificial, visualização interativa e planejamento de hábitos de consumo energético.

As bibliotecas e os modelos utilizados possuem licenças próprias. Os avisos de terceiros incluídos no repositório devem ser preservados.
