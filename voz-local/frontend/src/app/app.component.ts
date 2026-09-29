import { Component, computed, inject, OnDestroy, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { HttpEventType } from '@angular/common/http';
import { firstValueFrom, Subscription } from 'rxjs';
import { ApiService, errorMessage } from './core/api.service';
import { Health, JobState, JobSummary, Transcript, UploadOptions } from './core/models';
import { UploadComponent } from './features/upload.component';
import { ProcessingComponent } from './features/processing.component';
import { TranscriptComponent } from './features/transcript.component';
import { timeLabel } from './shared/time';
import { DialogFocusDirective } from './shared/dialog.directive';

@Component({ selector: 'app-root', standalone: true, imports: [DatePipe, UploadComponent, ProcessingComponent, TranscriptComponent, DialogFocusDirective], templateUrl: './app.component.html' })
export class AppComponent implements OnDestroy {
  api = inject(ApiService); jobs = signal<JobSummary[]>([]); selected = signal<Transcript | null>(null); state = signal<JobState | null>(null); health = signal<Health | null>(null);
  error = signal(''); busy = signal(false); loading = signal(false); uploadProgress = signal<number | null>(null); deleteMode = signal<'all' | 'audio' | null>(null); deleting = signal(false); canLoadMore = signal(false);
  activeId = signal<string | null>(null); time = timeLabel; private poll?: ReturnType<typeof setTimeout>; private uploadSubscription?: Subscription; private generation = 0; private destroyed = false;
  canDelete = computed(() => !!this.state() && ['COMPLETED', 'FAILED', 'QUEUED', 'UPLOADED'].includes(this.state()!.status));
  labels: Record<string, string> = { UPLOADED: 'Recebida', QUEUED: 'Na fila', PREPROCESSING: 'Preparando', TRANSCRIBING: 'Transcrevendo', DIARIZING: 'Identificando falantes', ALIGNING: 'Finalizando', COMPLETED: 'Concluída', FAILED: 'Falhou' };
  private onHashChange = () => {
    const id = location.hash.slice(1);
    if (/^[0-9a-f-]{36}$/i.test(id)) {
      if (id !== this.activeId()) void this.open(id);
      return;
    }
    if (!id && this.activeId()) this.newTranscription();
  };
  constructor() {
    window.addEventListener('hashchange', this.onHashChange);
    void this.initialize();
  }
  async initialize() {
    try {
      this.health.set(await firstValueFrom(this.api.health()));
      await this.refresh();
      const id = location.hash.slice(1);
      if (/^[0-9a-f-]{36}$/i.test(id)) await this.open(id);
    } catch (e) {
      this.error.set(errorMessage(e));
    }
  }
  async refresh(more = false) {
    try { const items = await firstValueFrom(this.api.list(more ? this.jobs().length : 0)); this.jobs.set(more ? [...this.jobs(), ...items] : items); this.canLoadMore.set(items.length === 50); } catch (e) { this.error.set(errorMessage(e)); }
  }
  newTranscription() { this.generation++; clearTimeout(this.poll); this.activeId.set(null); this.selected.set(null); this.state.set(null); this.error.set(''); this.loading.set(false); history.replaceState(null, '', location.pathname); }
  async open(id: string) {
    const generation = ++this.generation; clearTimeout(this.poll); this.activeId.set(id); this.selected.set(null); this.state.set(null); this.loading.set(true); this.error.set(''); history.replaceState(null, '', '#' + id);
    try { const result = await firstValueFrom(this.api.get(id)); if (generation !== this.generation || this.destroyed) return; this.selected.set(result); this.state.set(result); this.schedule(id, generation); } catch (e) { if (generation === this.generation) this.error.set(errorMessage(e)); } finally { if (generation === this.generation) this.loading.set(false); }
  }
  schedule(id: string, generation: number) {
    if (generation !== this.generation || this.destroyed || ['COMPLETED', 'FAILED'].includes(this.state()?.status ?? '')) return;
    this.poll = setTimeout(async () => {
      try { const state = await firstValueFrom(this.api.status(id)); if (generation !== this.generation || this.destroyed) return; this.error.set('');
        this.jobs.update(jobs => jobs.map(j => j.id === id ? { ...j, ...state } : j));
        if (state.status === 'COMPLETED' || state.status === 'FAILED') { const result = await firstValueFrom(this.api.get(id)); if (generation !== this.generation) return; this.selected.set(result); this.state.set(result); await this.refresh(); } else { this.state.set(state); }
      } catch (e) { if (generation === this.generation) this.error.set(errorMessage(e)); }
      this.schedule(id, generation);
    }, 2000);
  }
  upload(event: { file: File; options: UploadOptions }) {
    if (this.busy()) return; this.busy.set(true); this.uploadProgress.set(null); this.error.set('');
    this.uploadSubscription = this.api.upload(event.file, event.options).subscribe({ next: response => {
      if (response.type === HttpEventType.UploadProgress) this.uploadProgress.set(response.total ? Math.round(response.loaded / response.total * 100) : null);
      if (response.type === HttpEventType.Response && response.body) { this.busy.set(false); void this.refresh(); void this.open(response.body.id); }
    }, error: e => { this.busy.set(false); this.error.set(errorMessage(e)); }, complete: () => this.busy.set(false) });
  }
  async confirmDelete() {
    const id = this.activeId(), mode = this.deleteMode(); if (!id || !mode || this.deleting()) return; this.deleting.set(true);
    try { await firstValueFrom(this.api.delete(id, mode === 'audio')); this.deleteMode.set(null); if (mode === 'all') this.newTranscription(); else await this.open(id); await this.refresh(); } catch (e) { this.error.set(errorMessage(e)); this.deleteMode.set(null); } finally { this.deleting.set(false); }
  }
  ngOnDestroy() {
    this.destroyed = true;
    this.generation++;
    clearTimeout(this.poll);
    this.uploadSubscription?.unsubscribe();
    window.removeEventListener('hashchange', this.onHashChange);
  }
}
