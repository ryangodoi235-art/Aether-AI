# Validação — 25/09/2026

Python 3.12.14, Linux. Oito testes automatizados passaram: ligar/desligar, repetição e conflito, inexistente com log, persistência após recriar aplicação, dispositivo adicionado por configuração, indisponível, ação incompatível e validação de entradas.
Execução: python -m unittest discover -s tests -v

Não testado no Windows de Ryan; aguardando execução local. Nenhum hardware real ou modelo de IA testado. A biblioteca de testes emitiu aviso de descontinuação do adaptador httpx, sem falhas na execução; a dependência de teste está fixada em requirements-dev.txt.
