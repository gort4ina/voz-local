# Relatório de validação da entrega

## Evidência obtida

- **Backend: 47 testes pytest aprovados.** Upload real WAV/FFmpeg/libmagic, formato/MIME/tamanho/duração, upload sem Content-Length, Origin, status/HTTP202, edição, nomes, exportações, documento para RAG, reprodução Range, exclusão, retenção, claims concorrentes e recuperação de lease.
- **Alinhamento/merge:** testes de interseção temporal por palavra, mudanças de falante, empate, lacunas, intervalos inválidos, união de tracks duplicadas, fala simultânea, interrupções e limite de agrupamento.
- **Providers:** adapters exercitados com doubles somente nos testes; parâmetros VAD/word timestamps e argumentos Pyannote conferidos. Rejeição de pipeline remoto e falta de token verificadas.
- **Frontend: 2 testes temporais aprovados.** Verificação TypeScript estrita aprovada; build de produção Angular concluído, incluindo verificação dos templates.
- **Bundle Angular final:** aproximadamente 286,50 kB brutos / 80,59 kB estimados para transferência. A estimativa de transferência é do compilador, não medição de rede.
- **Lint/formatação Python:** Ruff check aprovado; 40 arquivos Python já formatados no conjunto app/tests.
- **Dependências de IA CPU instaladas e importadas juntas:** torch 2.8.0+cpu, torchaudio 2.8.0+cpu, torchcodec 0.7.0, Faster-Whisper 1.2.1 e pyannote.audio 4.0.3.
- **`uv pip check`:** 119 pacotes instalados verificados, sem incompatibilidades declaradas.
- **Docker/CI:** sintaxe YAML de Compose CPU, override GPU e workflow analisada; presença dos lockfiles e saída de build conferida.

O pytest emite um aviso de depreciação de `BlockingPortal` entre Starlette TestClient e AnyIO. Não houve falhas de teste. O aviso de cascata de exclusão SQL observado durante o desenvolvimento foi corrigido, com exclusão ordenada dos segmentos e falantes.

## Inferência real de transcrição

Faster-Whisper **tiny / CPU / int8** executado com o áudio público `jfk.flac` do conjunto de testes do próprio Faster-Whisper, convertido pelo serviço de áudio para WAV 16 kHz/mono. Resultado: idioma inglês, **22 palavras**, timestamps positivos e reconhecimento de uma expressão esperada. O tempo total observado de **57,99 segundos inclui inicialização/download**; não é benchmark de velocidade de inferência.

Fonte da amostra: https://github.com/SYSTRAN/faster-whisper/blob/master/tests/data/jfk.flac. Cópias de referência podem estar em `data/samples/` (jfk.flac / jfk.wav). Os pesos dos modelos não vêm no ZIP. Esse smoke test não avalia português, o modelo padrão `small` nem diarização multi-falante.

## Atualização — sessão de 2026-09-05 (Windows + Docker)

- **Docker Compose CPU** executado com sucesso (`api` healthy, `worker`, `frontend` em http://127.0.0.1:8080).
- **47 testes pytest** reexecutados no container da API: todos aprovados.
- **Inferência real end-to-end** com Faster-Whisper `small` + Pyannote Community-1 (token presente): amostra pública `jfk.wav` (~11 s), job `COMPLETED` em ~58 s de processamento, 1 falante / 5 segmentos, renomeação, edição e exportação TXT/JSON/SRT/VTT verificadas via API.
- A amostra JFK é mono-falante e em inglês; forçar `language=pt` degrada o texto (esperado). **Validação com dois falantes reais em português ainda deve ser feita pelo usuário** com gravação própria.
- Frontend: `npm test` (2) e build Docker Angular concluídos; correção de deep-link `#id` via listener `hashchange`.
- CUDA/GPU, carga de 120 min e PostgreSQL em produção continuam sem benchmark nesta máquina.

O checklist operacional permanece em `docs/ACEITE.md`. Use uma conversa curta com dois participantes para fechar o item de diarização multi-falante.

## Atualização — sessão de 2026-09-06 (instalação Windows)

- **Frontend local:** `npm ci`, lint TypeScript, 2 testes e `ng build` aprovados.
- **Docker Compose CPU:** serviços `api`, `worker` e `frontend` iniciados; health em `:8000` e UI em `:8080`.
- **Backend no container:** 47 testes pytest aprovados.
- **Python nativo no Windows:** pacotes de desenvolvimento instalam, mas o backend nativo falha sem `libmagic` (`ImportError: failed to find libmagic`). Caminho suportado: Docker/WSL2.
- Versões observadas nesta máquina: Python 3.12.10, Node 24.x (família aceita pelo Angular 20), Docker Engine/Compose recentes. O Dockerfile e o CI fixam Node **22.22.0**.
