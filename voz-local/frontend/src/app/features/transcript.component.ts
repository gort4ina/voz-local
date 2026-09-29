import { Component, ElementRef, inject, input, output, signal, ViewChild } from '@angular/core';
import { DecimalPipe } from '@angular/common';
import { FormControl, ReactiveFormsModule, Validators } from '@angular/forms';
import { firstValueFrom } from 'rxjs';
import { ApiService, errorMessage } from '../core/api.service';
import { ExportFormat, Speaker, Transcript } from '../core/models';
import { timeLabel } from '../shared/time';

@Component({
  selector: 'app-transcript',
  standalone: true,
  imports: [ReactiveFormsModule, DecimalPipe],
  template: `
    <section class="result-header panel">
      <div class="section-heading">
        <div>
          <span class="eyebrow">TRANSCRIÇÃO CONCLUÍDA</span>
          <h2>{{ transcript().original_filename }}</h2>
        </div>
        <span class="pill success">Concluída</span>
      </div>

      <div class="result-facts">
        <span>{{ time(transcript().duration) }} de áudio</span>
        <span>{{ transcript().speakers.length }} identificação(ões)</span>
        <span>{{ transcript().segments.length }} trechos</span>
        <span>{{ transcript().language.toUpperCase() }}</span>
      </div>

      @if (transcript().audio_available) {
        <audio
          #player
          controls
          preload="metadata"
          [src]="api.audioUrl(transcript().id)"
          (timeupdate)="trackTime()"
          (error)="audioError.set(true)"
          aria-label="Reproduzir gravação original"
        ></audio>
      } @else {
        <p class="muted">O áudio foi excluído. A transcrição continua disponível.</p>
      }

      @if (audioError()) {
        <p class="error">
          O navegador não conseguiu reproduzir o arquivo. Confira se o formato é compatível e se o servidor está disponível.
        </p>
      }

      <div class="export-bar">
        <label>
          Exportar como
          <select [formControl]="format">
            <option value="txt">Texto (.txt)</option>
            <option value="json">Dados completos (.json)</option>
            <option value="srt">Legendas (.srt)</option>
            <option value="vtt">WebVTT (.vtt)</option>
          </select>
        </label>
        <button class="button secondary" [disabled]="saving()" (click)="download()">
          Baixar transcrição ↓
        </button>
      </div>
    </section>

    @if (error()) {
      <p class="error" role="alert">{{ error() }}</p>
    }
    @if (notice()) {
      <p class="notice" role="status">{{ notice() }}</p>
    }

    <div class="review-layout">
      <aside class="panel participants">
        <span class="eyebrow">PARTICIPANTES</span>
        <h3>Quem está falando</h3>
        <p class="muted small">Ajuste os nomes para organizar a conversa.</p>

        @for (speaker of transcript().speakers; track speaker.id; let i = $index) {
          <div class="participant">
            <span class="avatar" [attr.data-color]="i % 4">{{ i + 1 }}</span>
            <div class="participant-content">
              @if (renaming() === speaker.id) {
                <label class="visually-hidden" [for]="'name-' + speaker.id">Nome do participante</label>
                <input [id]="'name-' + speaker.id" [formControl]="nameControl" maxlength="100">
                <div class="inline-actions">
                  <button class="text-button" (click)="saveName(speaker)" [disabled]="saving() || nameControl.invalid">Salvar</button>
                  <button class="text-button" (click)="renaming.set(null)" [disabled]="saving()">Cancelar</button>
                </div>
              } @else {
                <strong>{{ speaker.display_name }}</strong>
                <button class="text-button" (click)="rename(speaker)">Renomear</button>
              }
            </div>
          </div>
        }

        <div class="review-note">
          <strong>Revisão humana</strong>
          <p>Confira os nomes dos falantes. O texto permanece exatamente como reconhecido no áudio.</p>
          <p>A confiança exibida vem do reconhecimento das palavras; não mede a certeza sobre a identidade do falante.</p>
        </div>
      </aside>

      <section class="panel transcript">
        <div class="section-heading">
          <h3>Conversa</h3>
          <span class="muted small">Clique no horário para ouvir</span>
        </div>

        @for (segment of transcript().segments; track segment.id) {
          <article class="segment" [class.playing]="currentTime() >= segment.start && currentTime() < segment.end">
            <div class="segment-meta">
              <button
                class="timestamp"
                (click)="seek(segment.start)"
                [disabled]="!transcript().audio_available"
                [attr.aria-label]="'Reproduzir a partir de ' + time(segment.start)"
              >
                {{ time(segment.start) }} – {{ time(segment.end) }}
              </button>
              <span>{{ segment.duration | number:'1.1-1' }} s</span>
            </div>

            <div class="segment-heading">
              <span class="speaker-label" [attr.data-color]="speakerIndex(segment.speaker_id) % 4">
                <span class="speaker-number">{{ speakerIndex(segment.speaker_id) + 1 }}</span>
                {{ speakerName(segment.speaker_id) }}
              </span>
              <div class="segment-tags">
                @if (segment.overlap) { <span class="warning-tag">Fala simultânea</span> }
                @if (segment.needs_review) { <span class="warning-tag">Revisar atribuição</span> }
              </div>
            </div>

            <p class="segment-text">{{ segment.text }}</p>
            <div class="segment-footer">
              <span class="muted small">
                {{ segment.confidence === null
                  ? 'Confiança não disponível'
                  : 'Confiança das palavras: ' + (segment.confidence * 100).toFixed(0) + '%' }}
              </span>
            </div>
          </article>
        }
      </section>
    </div>
  `,
})
export class TranscriptComponent {
  api = inject(ApiService);
  transcript = input.required<Transcript>();
  changed = output<Transcript>();
  @ViewChild('player') player?: ElementRef<HTMLAudioElement>;
  currentTime = signal(-1);
  renaming = signal<string | null>(null);
  saving = signal(false);
  error = signal('');
  notice = signal('');
  audioError = signal(false);
  nameControl = new FormControl('', { nonNullable: true, validators: [Validators.required, Validators.maxLength(100)] });
  format = new FormControl<ExportFormat>('txt', { nonNullable: true });
  time = timeLabel;

  speakerIndex(id: string) {
    return this.transcript().speakers.findIndex(s => s.id === id);
  }

  speakerName(id: string) {
    return this.transcript().speakers.find(s => s.id === id)?.display_name ?? 'Falante não identificado';
  }

  trackTime() {
    this.currentTime.set(this.player?.nativeElement.currentTime ?? -1);
  }

  seek(seconds: number) {
    const audio = this.player?.nativeElement;
    if (audio) {
      audio.currentTime = seconds;
      audio.play().catch(() => this.error.set('Use o botão de reprodução do player para ouvir o áudio.'));
    }
  }

  rename(speaker: Speaker) {
    this.nameControl.setValue(speaker.display_name);
    this.renaming.set(speaker.id);
  }

  async saveName(speaker: Speaker) {
    if (this.saving() || !this.nameControl.value.trim()) return;
    this.saving.set(true);
    this.error.set('');
    try {
      this.changed.emit(await firstValueFrom(this.api.rename(this.transcript().id, speaker.id, this.nameControl.value.trim())));
      this.renaming.set(null);
      this.notice.set('Nome atualizado em toda a transcrição.');
    } catch (e) {
      this.error.set(errorMessage(e));
    } finally {
      this.saving.set(false);
    }
  }

  async download() {
    if (this.saving()) return;
    this.saving.set(true);
    this.error.set('');
    try {
      const blob = await firstValueFrom(this.api.export(this.transcript().id, this.format.value));
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `transcricao-${this.transcript().id}.${this.format.value}`;
      anchor.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) {
      this.error.set(errorMessage(e));
    } finally {
      this.saving.set(false);
    }
  }
}
