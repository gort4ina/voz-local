# Contratos e plano de implementação

## Fronteiras

1. `TranscriptionProvider.transcribe(path, language) -> (list[Word], language)`: timestamps em segundos, texto original de cada palavra e confiança opcional. O domínio não importa Faster-Whisper.
2. `DiarizationProvider.validate_configuration()` verifica requisitos locais antes do processamento; `diarize(path, SpeakerOptions) -> list[Turn]` retorna todos os intervalos, inclusive simultâneos. O domínio não importa Pyannote.
3. `AudioProcessingService` valida cabeçalhos/conteúdo e normaliza em arquivo. A API faz probe antes de aceitar; o worker faz decode integral.
4. `SegmentAlignmentService.align(words, turns)` pontua interseção temporal, mantém candidatos e identifica ambiguidade.
5. `SegmentMergeService.merge(segments, turns)` preserva limites de falante e palavras originais.
6. `TranscriptionService.process(job_id, lease_token)` orquestra transições e grava resultado atomicamente sob posse válida.
7. `AudioStorage` desacopla resolução/exclusão de arquivos. A implementação atual usa disco; trocar por armazenamento de objetos exige adaptar também ingestão/serving/temporários do pipeline, não apenas mudar uma URL.
8. `ResultService` centraliza leitura, alteração, remoção, retenção e `get_transcript_document`.

## Dados

`Transcription` contém metadata, status, opções, métricas, áudio, palavras brutas, turnos, timestamps e campos da lease. `Speaker` pertence à transcrição. `TranscriptionSegment` pertence à mesma transcrição, referencia Speaker e preserva duração derivada, texto atual/original, palavras, confiança, candidatos e flags de revisão. Os intervalos não possuem restrição de exclusividade: sobreposições são representáveis. A ordem de apresentação é `sequence`.

Os horários absolutos do banco são UTC sem offset internamente para comparações idênticas em SQLite e PostgreSQL; DTOs os serializam com `Z`. Timestamps de áudio são segundos relativos ao início do arquivo. Não se usa o horário de relógio como posição de áudio.

## Sequência de execução

O trabalho foi organizado em contratos/estrutura, backend e áudio, providers, alinhamento/persistência/fila, frontend/revisão, exportação, testes e Docker/documentação. Lint, testes e compilação foram executados em marcos de integração, corrigindo os problemas encontrados. Consulte o relatório de validação para os comandos efetivamente executados.

## Segurança operacional

Há limitação de corpo incluindo uploads chunked, validação de metadata e bytes, FFmpeg restrito a protocolos `file,pipe`, nome saneado, storage com UUID e verificação de caminho, erros sanitizados e rejeição de Origin desconhecida em escritas. API e worker não registram conteúdo de conversa. O deploy padrão é somente loopback. Não há autenticação ou criptografia implementada; a especificação pede preparação futura desses recursos.

## Extensões futuras

- Novos engines implementam os protocolos e são injetados no worker.
- Outra fila substitui claim/lease e entrega o job à mesma orquestração; o storage/banco precisam ser acessíveis a todos os workers.
- Para RAG, use o endpoint `/document`; nenhum envio externo é efetuado por esta versão.
- Para autenticação, adicione identidade nos routers e escopo/owner em todas as consultas e arquivos; CORS não substitui autorização.
- Para mudanças de schema após esta primeira versão, adicione migrações Alembic e procedimento de backup/upgrade. `create_all` não altera schemas existentes.
