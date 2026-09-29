# Dependências e compatibilidade

Verificação da entrega: 2026-09-04. Os metadados publicados foram consultados antes da instalação dos engines de IA. Os locks foram resolvidos para Python 3.12/Linux x86_64; não são uma promessa de compatibilidade binária universal.

| Componente | Versão fixada | Compatibilidade/decisão |
|---|---|---|
| Python | 3.12 | Executado em 3.12.13; Docker usa 3.12-slim-bookworm. |
| Angular core/CLI/build | 20.3.30 | Pacotes da mesma versão; standalone, signals e Reactive Forms. |
| TypeScript | 5.9.3 | Compatível com a linha Angular 20.3. |
| Node | 22.22.0 no Docker | Build local executado com Node 24.19.0. |
| FastAPI | 0.116.1 | API separada do worker; Pydantic 2.11.7. |
| SQLAlchemy | 2.0.43 | Modelos SQL portáveis; psycopg 3.2.9. |
| Faster-Whisper | 1.2.1 | Usa CTranslate2, VAD e word timestamps. |
| CTranslate2 | 4.6.0 | CUDA 12/cuDNN 9 na variante GPU; int8 na CPU. |
| pyannote.audio | 4.0.3 | Seus próprios metadados fixam torch 2.8.0, torchaudio 2.8.0 e torchcodec 0.7.0. |
| torch/torchaudio | 2.8.0 | Wheels +cpu no padrão; CUDA 12.8 na variante GPU. |
| TorchCodec | 0.7.0 | Par explícito exigido pelo Pyannote; FFmpeg disponível no sistema. |
| FFmpeg | Pacote Debian Bookworm | Inclui ffprobe; a versão do pacote de SO acompanha correções do repositório da distribuição. |
| Modelos | Whisper `small`; Community-1 | Pesos não incluídos; a revisão remota pode mudar. Para reprodutibilidade de pesos, mantenha uma cópia local autorizada e seu checksum. |

`requirements.txt` define dependências diretas da API. `requirements.lock` resolve as transitivas. `requirements-ml.txt` fixa o conjunto principal de IA; `requirements-ml.lock` resolve a variante CUDA e `requirements-ml-cpu.lock` resolve CPU. O lock CPU exige pré-instalar torch/torchaudio +cpu pelo índice oficial antes do `pip install -r`, como no Docker/README. O lock usa PyPI para as demais dependências. `package-lock.json` fixa dependências transitivas do frontend; use `npm ci`.

Os locks não foram gerados com hashes de wheels. Bibliotecas Python foram instaladas no ambiente de validação com o backend CPU; a verificação do gerenciador não encontrou dependências incompatíveis. Os imports de Faster-Whisper, Pyannote, torch, torchaudio e TorchCodec foram executados juntos com sucesso. A variante CUDA foi resolvida, mas não foi executada em GPU.

A API do Pyannote 4 utiliza `token=` e retorna um objeto com `speaker_diarization`; o adapter acessa sua Annotation regular para preservar sobreposição, em vez de usar apenas a diarização exclusiva. Isso é coberto por testes de contrato e documentação primária. Um token real e a aceitação dos termos são necessários para validar o carregamento dos pesos Community-1.

## Fontes primárias

- Faster-Whisper: https://github.com/SYSTRAN/faster-whisper
- Metadados Faster-Whisper 1.2.1: https://pypi.org/pypi/faster-whisper/1.2.1/json
- Metadados Pyannote 4.0.3: https://pypi.org/pypi/pyannote.audio/4.0.3/json
- Metadados PyTorch 2.8.0: https://pypi.org/pypi/torch/2.8.0/json
- Modelo Community-1, token, condições e execução local: https://huggingface.co/pyannote/speaker-diarization-community-1
- Pyannote: https://github.com/pyannote/pyannote-audio
- TorchCodec e matriz de versões: https://github.com/pytorch/torchcodec
- Compatibilidade Angular/Node/TypeScript: https://angular.dev/reference/versions

Bibliotecas e pesos mantêm suas licenças. Community-1 requer atribuição conforme CC-BY-4.0; preserve a referência ao modelo ao distribuir/adaptar seus pesos. Este projeto não redistribui pesos.

O conjunto de IA inclui `httpx[socks]` para ambientes que utilizam proxy SOCKS; isso não altera o processamento local.
