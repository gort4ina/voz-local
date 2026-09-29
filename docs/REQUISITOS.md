Você é um engenheiro de software sênior especializado em Python, processamento de áudio, Speech-to-Text, Machine Learning e aplicações web.

Sua tarefa é desenvolver uma aplicação web completa para **transcrição de arquivos de áudio com identificação de diferentes falantes (Speaker Diarization)**.

O sistema deve receber um arquivo de áudio contendo uma conversa entre duas ou mais pessoas e retornar uma transcrição estruturada identificando:

* o que foi falado;
* qual falante disse cada trecho;
* horário inicial de cada trecho;
* horário final de cada trecho;
* duração;
* nível de confiança, quando disponível.

Exemplo do resultado esperado:

```text
[00:00:03 - 00:00:08] Falante 1:
Olá, tudo bem? Como você está se sentindo hoje?

[00:00:09 - 00:00:14] Falante 2:
Estou um pouco melhor, mas ainda tenho dificuldade para dormir.

[00:00:15 - 00:00:18] Falante 1:
Quando você percebeu que isso começou?
```

IMPORTANTE:

Não confundir **Speaker Diarization** com reconhecimento biométrico de voz.

O sistema inicialmente deve identificar os participantes como:

* Falante 1
* Falante 2
* Falante 3
* etc.

Depois da transcrição, o usuário deverá poder alterar manualmente esses nomes.

Por exemplo:

```text
Falante 1 → Psicólogo
Falante 2 → Paciente
```

Após essa alteração, todos os trechos atribuídos àquele falante devem ser atualizados.

---

# 1. Objetivo da aplicação

Criar uma aplicação web onde seja possível:

1. enviar um arquivo de áudio;
2. processar o áudio;
3. detectar os diferentes participantes;
4. transcrever o conteúdo;
5. associar cada trecho ao respectivo falante;
6. apresentar a transcrição organizada cronologicamente;
7. reproduzir o áudio;
8. clicar em um trecho da transcrição e navegar para aquele ponto do áudio;
9. renomear os falantes;
10. editar manualmente a transcrição;
11. exportar o resultado.

A arquitetura deve ser preparada para posteriormente permitir que a transcrição seja enviada para uma API externa, RAG ou LLM.

---

# 2. Stack

Utilize preferencialmente:

## Frontend

Angular com:

* TypeScript;
* componentes standalone;
* signals quando fizer sentido;
* arquitetura modular;
* services para comunicação HTTP;
* interfaces/types bem definidos;
* Reactive Forms;
* design responsivo.

Utilizar uma interface limpa e profissional.

Não utilizar bibliotecas UI excessivamente pesadas se não forem necessárias.

---

## Backend

Utilizar:

```text
Python
FastAPI
Uvicorn
Pydantic
SQLAlchemy
```

Organizar o backend utilizando separação clara entre:

```text
routers
services
repositories
models
schemas
core
workers
transcription
diarization
audio
```

Não colocar toda a lógica dentro dos endpoints.

---

# 3. Motor de transcrição

Criar uma abstração:

```python
TranscriptionProvider
```

Exemplo:

```python
class TranscriptionProvider:
    async def transcribe(self, audio_path: str):
        ...
```

A implementação inicial deve utilizar uma solução local baseada em Whisper.

Priorizar:

```text
faster-whisper
```

ou, caso seja necessário para integração mais precisa entre timestamps e diarização:

```text
WhisperX
```

Escolha a alternativa tecnicamente mais adequada para conseguir:

* timestamps precisos;
* segmentação;
* reconhecimento em português;
* integração com speaker diarization;
* boa performance.

Não acoplar toda a aplicação diretamente a uma única biblioteca.

Criar providers para que futuramente seja possível substituir o motor por:

* OpenAI Speech-to-Text;
* AWS Transcribe;
* Google Speech-to-Text;
* Deepgram;
* AssemblyAI;
* outro serviço.

---

# 4. Speaker Diarization

Esta é uma funcionalidade essencial.

O sistema deve detectar automaticamente quando o falante muda.

Utilizar uma solução adequada de Speaker Diarization, preferencialmente baseada em:

```text
pyannote.audio
```

ou integração equivalente através do WhisperX.

O pipeline esperado conceitualmente é:

```text
Áudio
    ↓
Pré-processamento
    ↓
Voice Activity Detection
    ↓
Transcrição
    ↓
Speaker Diarization
    ↓
Alinhamento timestamps × falantes
    ↓
Agrupamento dos segmentos
    ↓
Transcrição final
```

O resultado interno deve permitir algo semelhante a:

```json
[
  {
    "speaker": "SPEAKER_00",
    "start": 3.12,
    "end": 8.54,
    "text": "Olá, tudo bem? Como você está se sentindo hoje?"
  },
  {
    "speaker": "SPEAKER_01",
    "start": 9.04,
    "end": 14.32,
    "text": "Estou melhor, mas ainda tenho dificuldade para dormir."
  }
]
```

Na interface converter:

```text
SPEAKER_00 → Falante 1
SPEAKER_01 → Falante 2
```

Não inventar a identidade real do participante.

---

# 5. Número de falantes

A aplicação deve trabalhar em dois modos.

### Automático

O modelo tenta determinar quantos falantes existem.

### Informado pelo usuário

Antes de iniciar o processamento, permitir opcionalmente informar:

```text
Número mínimo de falantes
Número máximo de falantes
```

ou:

```text
Número exato de falantes
```

Exemplo:

```text
Quantidade de participantes: 2
```

Quando essa informação estiver disponível, utilizá-la para melhorar a diarização.

---

# 6. Pré-processamento do áudio

Criar:

```text
AudioProcessingService
```

Utilizar FFmpeg quando necessário.

Normalizar os arquivos recebidos para um formato interno padronizado, por exemplo:

```text
WAV
16 kHz
mono
PCM
```

Aceitar inicialmente:

```text
.mp3
.wav
.m4a
.ogg
.webm
.mp4
```

O backend deve validar:

* extensão;
* MIME type;
* tamanho;
* duração;
* arquivo corrompido.

Nunca confiar apenas na extensão enviada pelo navegador.

---

# 7. Arquivos longos

O sistema deve suportar gravações longas.

Pensar desde o início em arquivos de:

```text
30 minutos
60 minutos
90 minutos
120 minutos
```

Não carregar desnecessariamente todo o arquivo na memória.

Utilizar processamento por arquivo/stream quando adequado.

Caso seja necessário dividir o áudio, implementar chunking de maneira que não destrua a continuidade da diarização.

Documentar as decisões tomadas.

---

# 8. Processamento assíncrono

A transcrição não deve bloquear uma requisição HTTP durante vários minutos.

Implementar conceito de Job.

Fluxo:

```text
POST /transcriptions

        ↓

upload do áudio

        ↓

criação do Job

        ↓

HTTP 202 Accepted

        ↓

processamento

        ↓

resultado armazenado
```

Status possíveis:

```text
UPLOADED
QUEUED
PREPROCESSING
TRANSCRIBING
DIARIZING
ALIGNING
COMPLETED
FAILED
```

Criar endpoint:

```http
GET /transcriptions/{id}/status
```

Retorno:

```json
{
  "id": "uuid",
  "status": "TRANSCRIBING",
  "progress": 42
}
```

No frontend exibir claramente o estágio atual.

Arquitetar de maneira que inicialmente seja possível executar jobs localmente, mas que futuramente seja simples migrar para:

```text
Redis
Celery
RQ
AWS SQS
AWS ECS
AWS Batch
```

---

# 9. Modelo de dados

Criar entidades aproximadamente como:

## Transcription

```text
id
original_filename
audio_path
status
language
duration
created_at
updated_at
processing_started_at
processing_finished_at
error_message
```

## Speaker

```text
id
transcription_id
internal_label
display_name
```

Exemplo:

```text
internal_label = SPEAKER_00
display_name = Falante 1
```

## TranscriptionSegment

```text
id
transcription_id
speaker_id
start_time
end_time
text
confidence
sequence
```

Manter o modelo preparado para PostgreSQL.

Para desenvolvimento local pode utilizar SQLite caso simplifique a execução, mas não criar código dependente especificamente de SQLite.

---

# 10. API

Implementar endpoints REST.

### Criar uma transcrição

```http
POST /api/transcriptions
```

Multipart form:

```text
audio
language
number_of_speakers
min_speakers
max_speakers
```

---

### Consultar status

```http
GET /api/transcriptions/{id}/status
```

---

### Consultar resultado

```http
GET /api/transcriptions/{id}
```

---

### Consultar segmentos

```http
GET /api/transcriptions/{id}/segments
```

---

### Alterar nome de falante

```http
PATCH /api/transcriptions/{id}/speakers/{speakerId}
```

Body:

```json
{
  "display_name": "Paciente"
}
```

---

### Editar segmento

```http
PATCH /api/transcriptions/{id}/segments/{segmentId}
```

Body:

```json
{
  "text": "Texto corrigido..."
}
```

---

### Excluir transcrição

```http
DELETE /api/transcriptions/{id}
```

---

# 11. Interface

Criar uma interface profissional.

Página inicial:

```text
Transcrição de áudio

[ arraste o arquivo até aqui ]

ou

[ Selecionar arquivo ]
```

Mostrar informações:

```text
arquivo
tamanho
duração
formato
```

Permitir selecionar:

```text
Idioma:
[ Português ]

Quantidade de falantes:
[ Detectar automaticamente ]

ou

[ 2 ]
```

Botão:

```text
Iniciar transcrição
```

---

# 12. Tela de processamento

Exibir:

```text
Processando gravação

✓ Arquivo recebido
✓ Preparando áudio
✓ Detectando fala
● Transcrevendo
○ Identificando falantes
○ Finalizando
```

Mostrar porcentagem quando for tecnicamente possível.

Não apresentar porcentagens falsas.

Se determinado modelo não fornecer progresso real, apresentar progresso baseado nas etapas do pipeline.

---

# 13. Tela de resultado

Criar um player de áudio no topo.

Abaixo:

```text
00:03 - 00:08

Falante 1

Olá, tudo bem? Como você está se sentindo hoje?


00:09 - 00:14

Falante 2

Estou um pouco melhor, mas ainda estou com dificuldade para dormir.
```

Cada falante deve possuir identificação visual consistente.

Não depender apenas da cor para diferenciar participantes.

Ao clicar no timestamp:

```text
00:09
```

o player deve navegar para:

```javascript
audio.currentTime = 9
```

Se possível, destacar automaticamente o segmento atual conforme o áudio é reproduzido.

---

# 14. Renomear falantes

Criar uma área:

```text
Participantes

Falante 1    [ Renomear ]
Falante 2    [ Renomear ]
```

Exemplo:

```text
Falante 1 → Psicólogo
Falante 2 → Paciente
```

A alteração deve refletir instantaneamente em toda a transcrição.

---

# 15. Edição da transcrição

Permitir editar manualmente qualquer segmento.

Exemplo:

```text
[editar]
```

Ao clicar:

```text
<textarea>
Estou melhor, mas ainda tenho dificuldade para dormir.
</textarea>

[Cancelar] [Salvar]
```

Persistir a alteração no backend.

---

# 16. Agrupamento inteligente

Os modelos podem gerar vários pequenos segmentos consecutivos do mesmo falante.

Implementar uma etapa:

```text
SegmentMergeService
```

Por exemplo:

```text
SPEAKER_00 00:01-00:04 "Bom dia."
SPEAKER_00 00:04-00:06 "Tudo bem?"
SPEAKER_00 00:06-00:09 "Como você está?"
```

Pode virar:

```text
SPEAKER_00
00:01-00:09

"Bom dia. Tudo bem? Como você está?"
```

Desde que não exista mudança de falante significativa entre eles.

Manter os timestamps originais internamente se forem úteis para sincronização.

---

# 17. Sobreposição de fala

Conversas reais possuem interrupções.

Exemplo:

```text
Pessoa A: Eu estava pensando que...

Pessoa B: Sim.

Pessoa A: ...talvez isso esteja relacionado...
```

A arquitetura deve ser preparada para lidar com segmentos sobrepostos retornados pelo modelo.

Não assumir que somente uma pessoa pode falar em determinado instante.

Caso a biblioteca escolhida não consiga transcrever perfeitamente sobreposição de voz, documentar essa limitação no README.

---

# 18. Estrutura

Organizar aproximadamente:

```text
/
├── frontend/
│   └── Angular
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── repositories/
│   │   ├── services/
│   │   ├── transcription/
│   │   │   ├── base.py
│   │   │   └── whisper_provider.py
│   │   ├── diarization/
│   │   │   ├── base.py
│   │   │   └── pyannote_provider.py
│   │   ├── audio/
│   │   ├── workers/
│   │   └── main.py
│   │
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
│
├── docker-compose.yml
├── .env.example
└── README.md
```

Pode adaptar a estrutura caso exista uma alternativa arquitetural melhor, mas justifique no README.

---

# 19. Configurações

Utilizar `.env`.

Exemplo:

```env
DATABASE_URL=
UPLOAD_DIR=
MAX_AUDIO_SIZE_MB=
DEFAULT_LANGUAGE=pt

WHISPER_MODEL=
WHISPER_DEVICE=
WHISPER_COMPUTE_TYPE=

HUGGINGFACE_TOKEN=
```

Nunca colocar tokens diretamente no código.

Criar:

```text
.env.example
```

com documentação de todas as variáveis.

Adicionar `.env` ao `.gitignore`.

---

# 20. Hugging Face / Pyannote

Caso o modelo de diarização utilizado necessite token do Hugging Face, implementar através de variável:

```env
HUGGINGFACE_TOKEN=
```

O README deve explicar claramente:

1. quais modelos são utilizados;
2. se é necessário aceitar os termos de determinado modelo;
3. onde obter o token;
4. onde configurar;
5. o que acontece quando não existe token.

Nunca inserir um token real no repositório.

---

# 21. CPU e GPU

O sistema deve conseguir detectar se CUDA está disponível.

Exemplo conceitual:

```python
if cuda_available:
    device = "cuda"
else:
    device = "cpu"
```

Permitir sobrescrever através do `.env`.

A aplicação deve funcionar sem GPU para desenvolvimento, ainda que de forma mais lenta.

Documentar claramente os requisitos para GPU.

---

# 22. Modelos Whisper

Permitir configurar modelos como:

```text
tiny
base
small
medium
large
```

Não espalhar o nome do modelo pelo código.

Utilizar configuração centralizada:

```env
WHISPER_MODEL=medium
```

Para português, selecionar uma configuração padrão razoável considerando qualidade versus consumo de recursos.

---

# 23. Separação de responsabilidades

Obrigatório criar interfaces equivalentes a:

```text
TranscriptionProvider
DiarizationProvider
AudioProcessingService
TranscriptionService
SegmentAlignmentService
SegmentMergeService
```

Fluxo:

```text
TranscriptionService
        │
        ├── AudioProcessingService
        │
        ├── TranscriptionProvider
        │
        ├── DiarizationProvider
        │
        ├── SegmentAlignmentService
        │
        └── SegmentMergeService
```

O domínio da aplicação não deve depender diretamente do Pyannote ou Whisper.

---

# 24. Resultado completo

Internamente criar um DTO semelhante a:

```json
{
  "id": "uuid",
  "language": "pt",
  "duration": 3584.32,
  "speakers": [
    {
      "id": "uuid",
      "internal_label": "SPEAKER_00",
      "display_name": "Falante 1"
    },
    {
      "id": "uuid",
      "internal_label": "SPEAKER_01",
      "display_name": "Falante 2"
    }
  ],
  "segments": [
    {
      "id": "uuid",
      "speaker_id": "uuid",
      "start": 3.12,
      "end": 8.54,
      "text": "Olá, tudo bem?",
      "confidence": 0.94
    }
  ]
}
```

---

# 25. Exportação

Implementar exportação para:

```text
TXT
JSON
SRT
VTT
```

TXT:

```text
[00:03] Psicólogo:
Como você está se sentindo hoje?

[00:09] Paciente:
Estou um pouco melhor.
```

JSON deve preservar:

```text
falantes
timestamps
segmentos
texto
metadata
```

---

# 26. Testes

Criar testes automatizados.

Backend:

```text
pytest
```

Testar principalmente:

* upload;
* validação;
* criação do job;
* atualização de status;
* renomeação de falante;
* edição de segmento;
* alinhamento entre diarização e transcrição;
* agrupamento de segmentos;
* tratamento de erros.

Não executar modelos gigantes dentro de testes unitários.

Utilizar mocks para:

```text
TranscriptionProvider
DiarizationProvider
```

Criar testes específicos para o algoritmo de alinhamento.

---

# 27. Docker

Criar:

```text
Dockerfile
docker-compose.yml
```

Permitir iniciar a aplicação com algo semelhante a:

```bash
docker compose up
```

O Docker deve contemplar FFmpeg e demais dependências necessárias.

Se GPU exigir configuração diferente, documentar separadamente.

---

# 28. Segurança

Validar todo upload.

Implementar:

* limite de tamanho;
* sanitização do nome;
* UUID para arquivos armazenados;
* validação de MIME;
* proteção contra path traversal;
* CORS configurável;
* mensagens de erro sem stack trace para o frontend.

Nunca utilizar diretamente o nome original como caminho físico.

Exemplo:

```text
uploads/
    025f24d1-a452-....wav
```

Armazenar o nome original apenas como metadata.

---

# 29. Privacidade

Como gravações podem conter dados confidenciais, preparar a arquitetura para:

* exclusão do áudio;
* exclusão da transcrição;
* políticas de retenção;
* storage desacoplado;
* criptografia futura;
* controle de acesso futuro.

Não enviar áudio para serviços externos silenciosamente.

A implementação padrão deve utilizar processamento local.

---

# 30. Logs

Implementar logs estruturados.

Registrar:

```text
job iniciado
pré-processamento
transcrição
diarização
alinhamento
conclusão
erro
tempo total
```

Nunca registrar a transcrição completa ou conteúdo sensível do áudio nos logs.

---

# 31. Métricas de processamento

Ao terminar, registrar metadata técnica:

```json
{
  "audio_duration_seconds": 3600,
  "processing_duration_seconds": 520,
  "transcription_duration_seconds": 340,
  "diarization_duration_seconds": 160,
  "segments": 342,
  "speakers": 2
}
```

Essas informações serão importantes posteriormente para analisar custos e performance.

---

# 32. Preparação para RAG

A aplicação futuramente enviará a transcrição para outro serviço.

Portanto criar uma representação limpa como:

```text
TranscriptDocument
```

Exemplo:

```json
{
  "transcription_id": "...",
  "duration": 3600,
  "participants": [
    "Psicólogo",
    "Paciente"
  ],
  "segments": [
    {
      "speaker": "Psicólogo",
      "start": 10.2,
      "end": 20.5,
      "text": "..."
    }
  ]
}
```

Criar um método:

```python
get_transcript_document(transcription_id)
```

que possa posteriormente ser enviado para:

```text
RAG
LLM
API
Vector Database
```

Não implementar RAG nesta etapa.

---

# 33. Qualidade da diarização

Dar atenção especial ao problema de relacionar a saída da transcrição com a saída da diarização.

Não fazer simplesmente:

```text
segmento 1 = speaker 1
segmento 2 = speaker 2
```

O sistema deve calcular a sobreposição temporal entre:

```text
segmentos de texto
```

e:

```text
segmentos de speaker diarization
```

para determinar o falante mais provável.

Criar um serviço específico:

```text
SegmentAlignmentService
```

Implementar e testar esse algoritmo separadamente.

Quando necessário, considerar alinhamento em nível de palavra.

---

# 34. Palavra por palavra

Se a biblioteca utilizada fornecer timestamps por palavra, preservar essa informação internamente.

Exemplo:

```json
{
  "word": "dormir",
  "start": 14.21,
  "end": 14.62,
  "speaker": "SPEAKER_01"
}
```

Isso pode aumentar significativamente a precisão da associação entre falantes.

Não é obrigatório exibir palavra por palavra na interface.

---

# 35. README

Criar README completo explicando:

```text
O que é o projeto
Arquitetura
Stack
Como instalar
Como executar
Configuração do Python
Configuração do Node
Configuração do Angular
FFmpeg
Whisper
Pyannote
Hugging Face
CPU
GPU
CUDA
Docker
Variáveis de ambiente
Endpoints
Testes
Limitações
```

Adicionar uma seção:

```text
Como funciona a transcrição
```

com o fluxo:

```text
Upload
↓
FFmpeg
↓
VAD
↓
Whisper
↓
Diarization
↓
Alignment
↓
Speaker Segments
↓
Persistência
↓
Frontend
```

---

# 36. Regras de implementação

Não:

* criar código fictício;
* deixar TODOs nas funcionalidades principais;
* criar funções vazias;
* retornar dados mockados no fluxo real;
* colocar toda a lógica dentro de controllers;
* ignorar tratamento de erros;
* instalar dependências incompatíveis;
* usar versões aleatórias de bibliotecas.

Antes de instalar as bibliotecas de IA, verificar compatibilidade entre:

```text
Python
PyTorch
CUDA
Whisper/Faster-Whisper/WhisperX
Pyannote
```

Selecionar versões compatíveis entre si e documentá-las.

---

# 37. Processo de execução no Cursor

Antes de escrever código:

1. analise todos os requisitos;
2. defina a arquitetura;
3. crie um plano de implementação;
4. identifique dependências;
5. identifique possíveis conflitos entre WhisperX, Pyannote, PyTorch e CUDA;
6. defina os contratos entre os componentes.

Depois implemente incrementalmente:

### Etapa 1

Estrutura do projeto.

### Etapa 2

Backend FastAPI.

### Etapa 3

Upload e processamento de áudio.

### Etapa 4

Whisper/Faster-Whisper.

### Etapa 5

Speaker Diarization.

### Etapa 6

Alinhamento transcrição × falantes.

### Etapa 7

Persistência.

### Etapa 8

Jobs assíncronos.

### Etapa 9

Frontend Angular.

### Etapa 10

Player sincronizado com transcrição.

### Etapa 11

Edição e renomeação de falantes.

### Etapa 12

Exportação.

### Etapa 13

Testes.

### Etapa 14

Docker.

### Etapa 15

README.

Após cada etapa:

* execute lint;
* execute testes existentes;
* corrija erros antes de continuar.

---

# 38. Critérios de aceite

A tarefa somente deve ser considerada concluída quando eu puder:

1. iniciar frontend e backend;
2. acessar a aplicação pelo navegador;
3. enviar um MP3/WAV;
4. iniciar uma transcrição;
5. acompanhar o processamento;
6. obter o texto transcrito;
7. visualizar ao menos dois falantes diferentes quando existirem;
8. visualizar os timestamps;
9. clicar em um timestamp e navegar para aquele ponto do áudio;
10. renomear "Falante 1" para outro nome;
11. visualizar a mudança em toda a transcrição;
12. editar um trecho;
13. exportar a transcrição;
14. excluir a transcrição;
15. executar os testes automatizados;
16. executar o projeto seguindo apenas as instruções do README.

Priorize principalmente:

**qualidade da transcrição, precisão dos timestamps, separação correta dos falantes, arquitetura extensível e facilidade de execução local.**

A funcionalidade mais importante do projeto não é apenas converter áudio em texto.

O diferencial obrigatório é:

**Transcrição + Speaker Diarization + timestamps + associação confiável entre cada trecho e seu respectivo falante.**
