import { AfterViewInit, Directive, ElementRef, HostListener, inject, OnDestroy } from '@angular/core';

@Directive({ selector: '[appDialogFocus]', standalone: true })
export class DialogFocusDirective implements AfterViewInit, OnDestroy {
  private host: ElementRef<HTMLElement> = inject(ElementRef);
  private previous = document.activeElement as HTMLElement | null;
  private focusables() { return Array.from(this.host.nativeElement.querySelectorAll<HTMLElement>('button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), a[href], [tabindex="0"]')); }
  ngAfterViewInit() { this.focusables()[0]?.focus(); }
  @HostListener('keydown', ['$event']) onKey(event: KeyboardEvent) {
    if (event.key !== 'Tab') return;
    const elements = this.focusables(), first = elements[0], last = elements[elements.length - 1];
    if (!first) { event.preventDefault(); return; }
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  }
  ngOnDestroy() { if (this.previous?.isConnected) this.previous.focus(); }
}
