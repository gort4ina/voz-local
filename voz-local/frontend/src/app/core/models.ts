export type JobStatus = 'UPLOADED' | 'QUEUED' | 'PREPROCESSING' | 'TRANSCRIBING' | 'DIARIZING' | 'ALIGNING' | 'COMPLETED' | 'FAILED';
export interface JobState { id: string; status: JobStatus; progress: number | null; progress_basis: 'stage'; error_message: string | null; attempts: number; updated_at: string; }
export interface JobSummary extends JobState { original_filename: string; language: string; duration: number; size_bytes: number; mime_type: string; audio_available: boolean; created_at: string; }
export interface Speaker { id: string; internal_label: string; display_name: string; }
export interface Segment { id: string; speaker_id: string; start: number; end: number; duration: number; text: string; original_text: string; confidence: number | null; sequence: number; overlap: boolean; needs_review: boolean; edited_at: string | null; candidate_labels: string[]; }
export interface Transcript extends JobSummary { speakers: Speaker[]; segments: Segment[]; metadata: Record<string, unknown>; processing_started_at: string | null; processing_finished_at: string | null; }
export interface UploadOptions { language: string; number_of_speakers?: number; min_speakers?: number; max_speakers?: number; }
export interface Health { status: string; processing: string; max_audio_size_mb: number; max_audio_duration_seconds: number; }
export type ExportFormat = 'txt' | 'json' | 'srt' | 'vtt';
