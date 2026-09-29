import { Component, input } from '@angular/core';
import { JobState } from '../core/models';

@Component({
  selector: 'app-processing',
  standalone: true,
  template: `
    <section class="panel processing" aria-live="polite">
      <span class="eyebrow">
        {{ state().status === 'FAILED' ? 'PROCESSAMENTO INTERROMPIDO' : 'TRANSCRIÇÃO EM ANDAMENTO' }}
      </span>
      <h2>{{ state().status === 'FAILED' ? 'Não foi possível concluir' : 'Processando gravação' }}</h2>
      <p class="muted">{{ filename() }}</p>

      @if (state().status === 'FAILED') {
        <p class="error" role="alert">{{ state().error_message }}</p>
      } @else {
        <ol class="stage-list">
          @for (step of steps; track step.status; let i = $index) {
            <li [class.done]="index() > i" [class.current]="index() === i">
              <span class="stage-marker" aria-hidden="true">{{ index() > i ? '✓' : i + 1 }}</span>
              <div>
                <strong>{{ step.label }}</strong>
                <span>{{ index() > i ? 'Concluído' : index() === i ? 'Em andamento' : 'Aguardando' }}</span>
              </div>
            </li>
          }
        </ol>
        <p class="muted small">
          O andamento é mostrado por etapas. O tempo depende da gravação e do computador.
          Você pode abrir outra transcrição e voltar depois.
        </p>
      }
    </section>
  `,
})
export class ProcessingComponent {
  state = input.required<JobState>();
  filename = input('');
  steps = [
    { status: 'QUEUED', label: 'Arquivo recebido · aguardando processamento' },
    { status: 'PREPROCESSING', label: 'Preparando áudio' },
    { status: 'TRANSCRIBING', label: 'Detectando fala e transcrevendo' },
    { status: 'DIARIZING', label: 'Identificando falantes' },
    { status: 'ALIGNING', label: 'Associando falantes e finalizando' },
  ];
  index() {
    return Math.max(0, this.steps.findIndex(s => s.status === this.state().status));
  }
}
