# Voz Local

Transcrição de áudio **com identificação de falantes** rodando 100% no seu servidor. Angular + FastAPI + Faster-Whisper + Pyannote. Exporta TXT, JSON, SRT e VTT. Sem envio para nuvem.

> Os falantes são rotulados como **Falante 1**, **Falante 2** etc. A aplicação **não** faz reconhecimento biométrico.

## Sumário

- [Instalação (Docker)](#instalação-docker)
- [Atualizar após mudar código](#atualizar-após-mudar-código)
- [Como usar](#como-usar)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Configuração (.env)](#configuração-env)
- [API HTTP](#api-http)
- [Desenvolvimento local (sem Docker)](#desenvolvimento-local-sem-docker)
- [GPU / CUDA](#gpu--cuda)
- [Testes](#testes)
- [Solução de problemas](#solução-de-problemas)
- [Referências](#referências)

---

## Instalação (Docker)

Caminho recomendado. Requer **Docker Desktop com WSL2** (Windows) ou Docker Engine + Compose v2 (Linux). Reserve ~16 GB de RAM e espaço em disco para imagens e modelos.

**1. Copie a configuração**

```powershell
# Windows
Copy-Item .env.example .env
```
```bash
# Linux/macOS
cp .env.example .env
```

**2. Configure o token do Hugging Face**

Aceite os termos do modelo de diarização com a mesma conta que vai gerar o token:

- Termos: https://huggingface.co/pyannote/speaker-diarization-community-1
- Token: https://huggingface.co/settings/tokens (permissão de leitura)

Edite **apenas** `.env`:

```env
HUGGINGFACE_TOKEN=hf_seu_token_aqui
```

**3. Suba os serviços**

```bash
docker compose up --build -d
```

**4. Acesse**

- Aplicação: http://127.0.0.1:8081
- API/Swagger: http://127.0.0.1:8001/docs

O primeiro processamento baixa os pesos dos modelos (leva alguns minutos). Sem token, a interface abre normalmente, mas cada job falha com mensagem pedindo o token.

**Encerrar sem apagar dados**

```bash
docker compose down
```

Os volumes `data` (banco/áudios) e `models` (cache) persistem. `docker compose down -v` **apaga** esses volumes.

---

## Atualizar após mudar código

Este é o ponto que costuma confundir: **`docker compose up` sozinho não reconstrói a imagem**. O Docker reutiliza a imagem antiga e você não vê suas mudanças.

### Frontend (mudou algo em `frontend/src/`)

Use o helper:

```powershell
# Windows
powershell -ExecutionPolicy Bypass -File scripts\rebuild-frontend.ps1
```
```bash
# Linux/macOS
./scripts/rebuild-frontend.sh
```

Ou manualmente:

```bash
docker compose build --pull frontend
docker compose up -d --force-recreate --no-deps frontend
```

Depois, no navegador, dê **Ctrl + F5** (hard refresh) para descartar o cache local. O Nginx já envia `Cache-Control: no-cache` no `index.html`, então em geral um refresh normal resolve.

### Backend (mudou algo em `backend/`)

```bash
docker compose up --build -d api worker
```

### Rebuild completo

```bash
docker compose build --no-cache
docker compose up -d --force-recreate
```

### Desenvolvimento sem Docker

Para iterar rápido no frontend, use `ng serve` em vez de rebuildar imagem toda vez:

```bash
cd frontend
npm install
npm start  # http://localhost:4200, proxy /api para :8001
```

O backend precisa estar acessível em `:8001` no host (via `docker compose up -d api worker` ou nativamente — ver [Desenvolvimento local](#desenvolvimento-local-sem-docker)).

---

## Como usar

1. **Envie o áudio** — arraste ou clique em Selecionar arquivo (MP3, WAV, M4A, OGG, WebM, MP4).
2. **Configure** — idioma e quantidade de falantes (automático, exato ou faixa mín/máx).
3. **Aguarde** — as etapas aparecem em tempo real. Você pode abrir outra transcrição e voltar depois.
4. **Revise** — clique num horário para ouvir o trecho. Renomeie falantes se quiser. O texto permanece como no áudio.
5. **Exporte** — TXT, JSON, SRT ou VTT.
6. **Limpe** — exclua só o áudio (mantém o texto) ou a transcrição inteira.

A URL usa `#<id>` para reabrir a mesma gravação. A lista lateral persiste no banco.

---

## Estrutura do projeto

```text
voz-local/
├── .env / .env.example        # configuração de runtime
├── docker-compose.yml         # perfil GPU/CUDA (padrão)
├── docker-compose.gpu.yml     # override GPU (compatibilidade)
├── backend/
│   ├── Dockerfile             # alvos: api, worker (CPU), worker-cuda (GPU)
│   ├── requirements*.txt      # dependências pinadas
│   └── app/
│       ├── api/               # routers FastAPI + middleware
│       ├── audio/             # validação e conversão FFmpeg
│       ├── core/              # config, db, logs, errors
│       ├── diarization/       # PyannoteProvider
│       ├── models/            # entidades SQLAlchemy
│       ├── repositories/      # transcrições + fila SQL
│       ├── schemas/           # DTOs
│       ├── services/          # upload, alinhamento, merge, export
│       ├── transcription/     # FasterWhisperProvider
│       └── workers/           # loop de processamento em processo separado
├── frontend/
│   ├── Dockerfile             # build Angular + Nginx
│   ├── nginx.conf             # proxy /api + cache headers
│   ├── angular.json
│   └── src/app/
│       ├── core/              # ApiService + modelos TypeScript
│       ├── features/          # upload, processing, transcript
│       └── shared/            # formatação de tempo, foco de dialog
├── scripts/
│   ├── rebuild-frontend.ps1   # helper Windows
│   ├── rebuild-frontend.sh    # helper Linux/macOS
│   ├── check-ml.py            # imports de IA
│   └── smoke-real.py          # transcrição real end-to-end
├── data/samples/              # jfk.flac / jfk.wav (amostras de referência)
└── docs/
    ├── ACEITE.md              # rastreabilidade dos requisitos
    ├── VALIDACAO.md           # relatório de validação
    ├── DEPENDENCIAS.md        # versões e compatibilidade
    └── REQUISITOS.md          # documento original de requisitos
```

### Fluxo de dados

```text
upload → FFmpeg (WAV 16 kHz mono) → VAD + Faster-Whisper → Pyannote
      → alinhamento por interseção temporal → agrupamento → SQLite
      → Angular
```

---

## Configuração (.env)

Todas as variáveis principais e seus padrões no Docker:

| Variável | Padrão | Uso |
|---|---|---|
| `DATABASE_URL` | `sqlite:////data/voz.db` | PostgreSQL: `postgresql+psycopg://user:senha@host/db` (escape a senha). |
| `UPLOAD_DIR` | `/data/uploads` | Diretório privado de áudio. |
| `MAX_AUDIO_SIZE_MB` | `512` | Limite por arquivo. Ao aumentar, ajuste também `client_max_body_size` no `nginx.conf`. |
| `MAX_AUDIO_DURATION_SECONDS` | `7200` | Limite de duração (2 h). |
| `DEFAULT_LANGUAGE` | `pt` | Idioma padrão quando omitido. |
| `CORS_ORIGINS` | JSON com `localhost:4200,8081` | Origens permitidas na API. |
| `WHISPER_MODEL` | `small` | `tiny`, `base`, `small`, `medium`, `large-v3` ou diretório. |
| `WHISPER_DEVICE` | `cuda` | `auto`, `cpu`, `cuda`. |
| `WHISPER_COMPUTE_TYPE` | `int8_float16` | CPU → `int8`; CUDA → `int8_float16`. |
| `DIARIZATION_DEVICE` | `cpu` | Independente da transcrição; use `cuda` se houver VRAM sobrando. |
| `DIARIZATION_MODEL` | Community-1 | Pyannote ID ou diretório local. |
| `HUGGINGFACE_TOKEN` | vazio | **Obrigatório** para a diarização. |
| `HF_HOME` | `/models` | Cache dos pesos (volume persistido). |
| `JOB_LEASE_SECONDS` | `180` | Lease do worker (mín. 30 s). |
| `JOB_MAX_ATTEMPTS` | `3` | Máx. tentativas de recuperação. |
| `RETENTION_DAYS` | `0` | `0` = sem expiração; positivo remove jobs terminais mais antigos. |

Após alterar `.env`, recrie os containers: `docker compose up -d --force-recreate`.

---

## API HTTP

| Método | Endpoint | Uso |
|---|---|---|
| `GET` | `/api/health` | Estado e limites. |
| `POST` | `/api/transcriptions` | Multipart: `audio`, `language`, `number_of_speakers` ou `min_speakers`/`max_speakers`. Retorna **202**. |
| `GET` | `/api/transcriptions?limit=50&offset=0` | Histórico paginado. |
| `GET` | `/api/transcriptions/{id}/status` | Estado, etapa e erro. |
| `GET` | `/api/transcriptions/{id}` | Metadata, falantes e segmentos. |
| `GET` | `/api/transcriptions/{id}/segments` | Segmentos ordenados. |
| `GET` | `/api/transcriptions/{id}/audio` | Áudio original (suporta Range/206). |
| `PATCH` | `/api/transcriptions/{id}/speakers/{sid}` | `{"display_name":"..."}`. |
| `GET` | `/api/transcriptions/{id}/export?format=json` | `txt`, `json`, `srt`, `vtt`. |
| `GET` | `/api/transcriptions/{id}/document` | Documento estruturado para integração. |
| `DELETE` | `/api/transcriptions/{id}/audio` | Exclui só o áudio (mantém texto). |
| `DELETE` | `/api/transcriptions/{id}` | Exclui tudo. HTTP 204. |

Exemplo:

```powershell
curl.exe -F "audio=@C:\Audios\conversa.mp3" `
         -F "language=pt" `
         -F "number_of_speakers=2" `
         http://127.0.0.1:8001/api/transcriptions
```

Estados de um job:

```
UPLOADED → QUEUED → PREPROCESSING → TRANSCRIBING → DIARIZING → ALIGNING → COMPLETED
                                                                        ↘ FAILED
```

---

## Desenvolvimento local (sem Docker)

Recomendado só em Linux/WSL2 (o Windows nativo esbarra em `libmagic` e no FFmpeg).

**Dependências de sistema (Debian/Ubuntu):**

```bash
sudo apt-get update
sudo apt-get install -y python3.12-venv ffmpeg libmagic1 libsndfile1
```

**Backend:**

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install torch==2.8.0+cpu torchaudio==2.8.0+cpu --index-url https://download.pytorch.org/whl/cpu
pip install -r backend/requirements-ml-cpu.lock
pip install -r backend/requirements-dev.txt
cp .env.example .env
```

Ajuste o `.env` para caminhos locais:

```env
DATABASE_URL=sqlite:///./data/voz.db
UPLOAD_DIR=./data/uploads
HF_HOME=./models-cache
HUGGINGFACE_TOKEN=hf_...
WHISPER_DEVICE=cpu
DIARIZATION_DEVICE=cpu
```

Em dois terminais (na pasta `backend/`, com `.venv` ativa):

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8001 --no-access-log
python -m app.workers.run
```

**Frontend:**

```bash
cd frontend
npm ci
npm start   # http://localhost:4200
```

O `proxy.conf.json` direciona `/api` para `127.0.0.1:8001`.

---

## GPU / CUDA

Padrão. Requer GPU NVIDIA, driver compatível e NVIDIA Container Toolkit (Docker Desktop com suporte NVIDIA no Windows).

```bash
docker compose up --build -d
```

O worker usa a imagem `worker-cuda` e força Whisper em CUDA (falha imediatamente se a GPU não estiver disponível). A diarização fica em CPU por padrão para caber em GPUs com pouca VRAM (ex.: GTX 1650 4 GB). Valide antes: `nvidia-smi` no host **e** dentro do container.

**Sugestão para GTX 1650 / VRAM limitada:** `WHISPER_MODEL=base` ou `small` com `WHISPER_COMPUTE_TYPE=int8_float16`. Se der OOM no Whisper, reduza o modelo. Se quiser diarização na GPU e houver VRAM, defina `DIARIZATION_DEVICE=cuda` no `.env` e no `environment` do compose.

---

## Testes

**Backend** (na `.venv`):

```bash
cd backend
ruff check app tests
ruff format --check app tests
pytest -q
```

47 testes cobrem upload, HTTP 202/status, alinhamento, merge, renomeação, exportações, exclusão, retenção, concorrência e recuperação de leases. Não baixam modelos.

**Frontend:**

```bash
cd frontend
npm ci
npm run lint     # TypeScript estrito
npm test         # 2 testes de formatação temporal
npm run build    # também valida templates Angular
```

**Smoke real** (requer token e `.env` configurado):

```bash
python scripts/check-ml.py                            # imports de IA
python scripts/smoke-real.py /caminho/absoluto/conversa.wav
```

O smoke usa providers reais e salva `data/smoke-result.json`.

---

## Solução de problemas

**Alterei o frontend mas o Docker mostra a versão antiga.**
`docker compose up` reutiliza a imagem em cache. Rode `scripts/rebuild-frontend.ps1` (ou `.sh`) e faça **Ctrl+F5** no navegador. O Nginx agora envia `Cache-Control: no-cache` no `index.html` e `immutable` nos assets com hash, então rebuild + refresh normal já resolve.

**Container `frontend` recriado, mas ainda vejo o layout antigo.**
Cache do navegador. Force refresh (**Ctrl+F5** / **Cmd+Shift+R**) ou abra em aba anônima. Se persistir, `docker exec voz-local-frontend-1 ls /usr/share/nginx/html` mostra qual bundle está servindo — o hash deve bater com o do `dist/` local.

**Job preso em `QUEUED`.**
Cheque `docker compose logs -f worker`. Sem o `HUGGINGFACE_TOKEN` correto, o worker marca `FAILED` com mensagem explícita.

**`Token/acesso negado`.**
Aceite os termos do modelo com a mesma conta do token. Depois: `docker compose up -d --force-recreate worker`.

**HTTP 413 no upload.**
Ajuste `MAX_AUDIO_SIZE_MB` no `.env` **e** `client_max_body_size` em `frontend/nginx.conf`, depois `docker compose up -d --build --force-recreate frontend api`.

**Áudio não toca no navegador.**
Depende do codec. MP4/M4A/OGG podem falhar em alguns navegadores mesmo com o processamento no servidor OK. WAV e MP3 são os caminhos mais estáveis.

**Memória / OOM.**
Reduza `WHISPER_MODEL` (para `base` ou `small`), use `WHISPER_DEVICE=cpu`, ou diminua a duração do áudio.

**Windows nativo: `ImportError: failed to find libmagic`.**
Esperado. Use Docker/WSL2.

---

## Referências

- Requisitos originais: [`docs/REQUISITOS.md`](docs/REQUISITOS.md)
- Rastreabilidade de aceite: [`docs/ACEITE.md`](docs/ACEITE.md)
- Relatório de validação: [`docs/VALIDACAO.md`](docs/VALIDACAO.md)
- Versões e compatibilidade: [`docs/DEPENDENCIAS.md`](docs/DEPENDENCIAS.md)

**Limites de implantação:** os serviços do Compose ligam em `127.0.0.1`. Esta é uma aplicação local, **sem** autenticação, multiusuário ou criptografia de banco. Não exponha na internet sem adicionar TLS, autenticação, quotas e governança.
