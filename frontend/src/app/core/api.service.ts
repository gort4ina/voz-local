import { inject, Injectable } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { ExportFormat, Health, JobState, JobSummary, Transcript, UploadOptions } from './models';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private http = inject(HttpClient);
  private base = '/api/transcriptions';
  health() { return this.http.get<Health>('/api/health'); }
  list(offset = 0) { return this.http.get<JobSummary[]>(this.base, { params: { limit: 50, offset } }); }
  get(id: string) { return this.http.get<Transcript>(`${this.base}/${id}`); }
  status(id: string) { return this.http.get<JobState>(`${this.base}/${id}/status`); }
  upload(file: File, options: UploadOptions) {
    const form = new FormData(); form.append('audio', file);
    Object.entries(options).forEach(([key, value]) => { if (value !== undefined) form.append(key, String(value)); });
    return this.http.post<JobState>(this.base, form, { observe: 'events', reportProgress: true });
  }
  rename(id: string, speakerId: string, name: string) { return this.http.patch<Transcript>(`${this.base}/${id}/speakers/${speakerId}`, { display_name: name }); }
  delete(id: string, audioOnly = false) { return this.http.delete<void>(`${this.base}/${id}${audioOnly ? '/audio' : ''}`); }
  audioUrl(id: string) { return `${this.base}/${id}/audio`; }
  export(id: string, format: ExportFormat) { return this.http.get(`${this.base}/${id}/export`, { params: { format }, responseType: 'blob' }); }
}
export function errorMessage(error: unknown): string {
  if (error instanceof HttpErrorResponse) {
    if (error.status === 0) return 'Não foi possível conectar ao servidor local. Confira se a aplicação está em execução.';
    if (typeof error.error?.detail === 'string') return error.error.detail;
    if (error.status === 413) return 'O arquivo excede o limite permitido pelo servidor.';
  }
  return 'Não foi possível concluir a operação. Tente novamente.';
}
