import { Component, input, output, signal, OnDestroy } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { UploadOptions } from '../core/models';
import { timeLabel } from '../shared/time';

@Component({
  selector: 'app-upload', standalone: true, imports: [ReactiveFormsModule],
  template: `
    <section class="panel upload-panel">
      <div class="section-heading">
        <div>
          <span class="eyebrow">NOVA GRAVAÇÃO</span>
          <h2>Transcrição de áudio</h2>
        </div>
        <span class="pill">Processamento local</span>
      </div>

      <p class="muted">Envie uma conversa para transcrever e identificar os diferentes falantes.</p>

      <form [formGroup]="form" (ngSubmit)="submit()">
        <div class="dropzone" [class.dragging]="dragging()" (dragover)="$event.preventDefault(); dragging.set(true)" (dragleave)="dragging.set(false)" (drop)="drop($event)">
          <span class="upload-symbol" aria-hidden="true">↑</span>
          <h3>{{ file() ? file()!.name : 'Arraste seu áudio até aqui' }}</h3>
          <p>{{ file() ? 'Arquivo selecionado e pronto para envio.' : 'ou selecione um arquivo no seu computador' }}</p>
          <input #picker class="visually-hidden" type="file" accept=".mp3,.wav,.m4a,.ogg,.webm,.mp4" (change)="choose($event)" [disabled]="busy()" aria-label="Selecionar arquivo de áudio">
          <button type="button" class="button secondary" (click)="picker.click()" [disabled]="busy()">
            {{ file() ? 'Trocar arquivo' : 'Selecionar arquivo' }}
          </button>
          <small>MP3, WAV, M4A, OGG, WebM ou MP4 · até {{ maxSize() }} MB · {{ maxDuration() / 60 }} min</small>
        </div>

        @if (file(); as selected) {
          <div class="file-facts">
            <span><b>Tamanho</b> {{ (selected.size / 1048576).toFixed(2) }} MB</span>
            <span><b>Duração</b> {{ duration() === null ? 'Validando...' : time(duration()!) }}</span>
            <span><b>Formato</b> {{ selected.name.split('.').pop()?.toUpperCase() }}</span>
          </div>
        }

        <div class="form-grid">
          <label>
            Idioma
            <select formControlName="language">
              <option value="pt">Português</option>
              <option value="auto">Detectar automaticamente</option>
              <option value="en">Inglês</option>
              <option value="es">Espanhol</option>
              <option value="fr">Francês</option>
              <option value="de">Alemão</option>
              <option value="it">Italiano</option>
            </select>
          </label>

          <label>
            Modo de Falantes
            <select formControlName="mode">
              <option value="auto">Detectar automaticamente</option>
              <option value="exact">Quantidade exata</option>
              <option value="range">Faixa (Mín/Máx)</option>
            </select>
          </label>

          @if (form.controls.mode.value === 'exact') {
            <label>
              Quantidade exata
              <input type="number" formControlName="exact" min="1" max="32" placeholder="Ex: 2">
            </label>
          }
          @if (form.controls.mode.value === 'range') {
            <div class="form-row">
              <label>Mínimo<input type="number" formControlName="min" min="1" max="32" placeholder="1"></label>
              <label>Máximo<input type="number" formControlName="max" min="1" max="32" placeholder="4"></label>
            </div>
          }
        </div>

        @if (error()) {
          <p role="alert" class="error">{{ error() }}</p>
        }

        <div class="upload-footer">
          <p class="muted small">
            O áudio é processado localmente neste servidor.<br>
            Os participantes serão identificados como “Falante 1”, “Falante 2”, etc.
          </p>
          <button class="button primary" type="submit" [disabled]="busy() || !file()">
            {{ busy() ? 'Enviando áudio…' : 'Iniciar transcrição' }}
            <span aria-hidden="true">→</span>
          </button>
        </div>

        @if (busy()) {
          <div class="upload-progress">
            <div class="upload-progress-meta">
              <span>{{ uploadProgress() === null ? 'Enviando e validando arquivo…' : 'Enviando arquivo...' }}</span>
              @if (uploadProgress() !== null) { <span>{{ uploadProgress() }}%</span> }
            </div>
            <div class="progress-container">
              <div class="progress-bar" [style.width]="(uploadProgress() ?? 0) + '%'"></div>
            </div>
          </div>
        }
      </form>
    </section>
  `,
})
export class UploadComponent implements OnDestroy {
  busy = input(false); uploadProgress = input<number | null>(null); maxSize = input(512); maxDuration = input(7200);
  requested = output<{ file: File; options: UploadOptions }>();
  file = signal<File | null>(null); duration = signal<number | null>(null); dragging = signal(false); error = signal('');
  time = timeLabel; private objectUrl = ''; private probe: HTMLAudioElement | null = null;
  form = new FormGroup({
    language: new FormControl('pt', { nonNullable: true }),
    mode: new FormControl('auto', { nonNullable: true }),
    exact: new FormControl(2, [Validators.min(1), Validators.max(32)]),
    min: new FormControl(2),
    max: new FormControl(4)
  });

  choose(event: Event) {
    const f = (event.target as HTMLInputElement).files?.[0];
    if (f) this.setFile(f);
  }

  drop(event: DragEvent) {
    event.preventDefault();
    this.dragging.set(false);
    const f = event.dataTransfer?.files[0];
    if (f && !this.busy()) this.setFile(f);
  }

  setFile(file: File) {
    this.error.set('');
    if (!/\.(mp3|wav|m4a|ogg|webm|mp4)$/i.test(file.name)) {
      this.error.set('Selecione um dos formatos de áudio aceitos.');
      return;
    }
    if (!file.size || file.size > this.maxSize() * 1048576) {
      this.error.set('O arquivo está vazio ou excede o tamanho permitido.');
      return;
    }
    this.release();
    this.file.set(file);
    this.duration.set(null);
    this.objectUrl = URL.createObjectURL(file);
    const probe = new Audio();
    this.probe = probe;
    probe.preload = 'metadata';
    probe.onloadedmetadata = () => {
      if (this.probe === probe && Number.isFinite(probe.duration)) this.duration.set(probe.duration);
    };
    probe.src = this.objectUrl;
  }

  submit() {
    const file = this.file(); if (!file || this.busy()) return;
    const v = this.form.getRawValue();
    const options: UploadOptions = { language: v.language };
    const valid = (x: number | null) => x !== null && Number.isInteger(x) && x >= 1 && x <= 32;

    if (v.mode === 'exact') {
      if (!valid(v.exact)) { this.error.set('Informe uma quantidade inteira entre 1 e 32.'); return; }
      options.number_of_speakers = v.exact!;
    }
    if (v.mode === 'range') {
      if (!valid(v.min) || !valid(v.max) || v.min! > v.max!) {
        this.error.set('Informe mínimo e máximo válidos, entre 1 e 32.');
        return;
      }
      options.min_speakers = v.min!;
      options.max_speakers = v.max!;
    }
    if ((this.duration() ?? 0) > this.maxDuration()) {
      this.error.set('A duração do arquivo excede o limite permitido.');
      return;
    }
    this.error.set('');
    this.requested.emit({ file, options });
  }

  release() {
    if (this.probe) {
      this.probe.onloadedmetadata = null;
      this.probe.removeAttribute('src');
      this.probe.load();
      this.probe = null;
    }
    if (this.objectUrl) URL.revokeObjectURL(this.objectUrl);
  }

  ngOnDestroy() { this.release(); }
}
