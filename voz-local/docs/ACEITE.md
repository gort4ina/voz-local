# Rastreabilidade dos requisitos e aceite

Implementado não significa comprovado com modelos reais ou em qualquer hardware. A coluna de verificação registra a evidência disponível nesta entrega.

| Itens do Markdown | Implementação | Verificação |
|---|---|---|
| 1–2: aplicação e stack | Angular standalone, signals/Reactive Forms; FastAPI/Pydantic/SQLAlchemy | Build Angular, TypeScript e testes HTTP. |
| 3–5: transcrição, diarização e quantidade | FasterWhisperProvider; PyannoteProvider; automático/exato/faixa | Imports reais, inferência ASR tiny/CPU e testes de adapters; pesos de diarização dependem de token. |
| 6–7: áudio e arquivos longos | libmagic + ffprobe, FFmpeg 16 kHz/mono, limite 7200 s | Teste com WAV real, tamanho/duração e normalização. Sem benchmark de 120 min. |
| 8–10: jobs, dados e API | Fila SQL, processo separado, leases, entidades, endpoints | HTTP202/status, concorrência, recuperação e persistência testados. |
| 11–15: interface e revisão | Dropzone, opções, estágios, player, seek, renomeação/edição | Angular/TypeScript compilam; APIs de edição testadas. Sem execução automatizada de navegador. |
| 16–17: agrupamento e sobreposição | Merge com limites/interrupções, turnos sobrepostos e flags | Testes específicos de interseção, empate, lacuna, overlap e merge. |
| 18–24: estrutura/configuração/providers/DTO | Módulos separados, .env, CPU/GPU, contratos | Lint e contratos testados; imports CPU executados. GPU não disponível. |
| 25: exportações | TXT/JSON/SRT/VTT e documento de integração | Exportações pós-edição e timestamps testados. |
| 26: testes | pytest + mocks apenas nos testes; testes temporais frontend | Resultado em VALIDACAO.md. |
| 27: Docker | API, worker CPU/GPU, frontend/Nginx, volumes | Compose CPU executado com sucesso (api healthy, worker, frontend em :8080). Ver VALIDACAO.md. |
| 28–31: segurança/privacidade/logs/métricas | Limites, saneamento, exclusão, retenção, logs JSON, métricas | Testes de upload, erros seguros, deleção e retenção. |
| 32–34: RAG e associação confiável | TranscriptDocument; alinhamento por palavra/interseção | Testes independentes e teste HTTP de documento. |
| 35–37: README, compatibilidade e execução | README, docs técnicos, locks, CI, smoke real | Versões instaladas/checadas em CPU; processo incremental em marcos de integração. |
| 38: aceite operacional | Fluxo implementado de upload a exclusão | Precisa fechar validação local com token, gravação real de dois falantes e navegador. |

## Passo final de aceite na máquina de destino

Use uma gravação curta não sensível com dois participantes reais. Inicie Docker conforme README, envie MP3/WAV, acompanhe a conclusão, confira palavras/timestamps e se os dois falantes foram separados corretamente. Clique em timestamps, renomeie um falante, edite um trecho, reabra/recarregue e confira persistência. Baixe os quatro formatos e confira nomes/textos alterados. Exclua só o áudio e confirme que texto permanece; por fim exclua tudo. Execute testes automatizados.

Registre resultado e hardware. Este passo não foi marcado como concluído sem evidência. O número solicitado de falantes orienta o modelo, mas a precisão da atribuição precisa ser avaliada; não se fabricam identidades para passar no aceite.
