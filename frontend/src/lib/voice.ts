/**
 * lib/voice.ts
 * Frontend Voice Mode Engine for ClaimSaathi.
 * Handles:
 * 1. State machine management (IDLE -> LISTENING -> TRANSCRIBING -> THINKING -> SPEAKING)
 * 2. Audio recording via MediaRecorder with Safari/iOS MIME detection
 * 3. Energy-based level meter & silence detection (VAD)
 * 4. Dual-tier Speech Providers (Gemini Audio API vs Browser Web Speech API)
 * 5. Audio playback queue with sentence synchronization and barge-in (<300ms stop)
 */

export type VoiceState =
  | "IDLE"
  | "LISTENING"
  | "TRANSCRIBING"
  | "THINKING"
  | "SPEAKING"
  | "ERROR"
  | "PERMISSION_DENIED";

export type VoiceLanguage = "auto" | "hi" | "en";

export interface VoiceConfig {
  enabled: boolean;
  gemini_stt_available: boolean;
  gemini_tts_available: boolean;
  default_voice_hi: string;
  default_voice_en: string;
  max_seconds: number;
}

export interface TranscriptionResult {
  text: string;
  language: "en" | "hi" | "hinglish";
  confidence: number;
  low_confidence_spans: string[];
  contains_amounts_or_dates: boolean;
}

/** Detects best supported MIME type for MediaRecorder on current browser */
export function getSupportedAudioMimeType(): string {
  if (typeof window === "undefined" || typeof MediaRecorder === "undefined") {
    return "audio/webm";
  }
  const types = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/mp4",
    "audio/aac",
    "audio/ogg;codecs=opus",
    "audio/wav",
  ];
  for (const t of types) {
    if (MediaRecorder.isTypeSupported(t)) {
      return t;
    }
  }
  return "";
}

/** Check if Web Speech Recognition is natively supported */
export function isBrowserSpeechRecognitionSupported(): boolean {
  if (typeof window === "undefined") return false;
  return "webkitSpeechRecognition" in window || "SpeechRecognition" in window;
}

/** Check if Web Speech Synthesis is natively supported */
export function isBrowserSpeechSynthesisSupported(): boolean {
  if (typeof window === "undefined") return false;
  return "speechSynthesis" in window && "SpeechSynthesisUtterance" in window;
}

/** Audio Context unlocker for mobile browsers */
let globalAudioCtx: AudioContext | null = null;
export function getOrCreateAudioContext(): AudioContext {
  if (typeof window === "undefined") {
    throw new Error("AudioContext only available in browser");
  }
  if (!globalAudioCtx || globalAudioCtx.state === "closed") {
    const AudioCtxClass = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    globalAudioCtx = new AudioCtxClass();
  }
  if (globalAudioCtx.state === "suspended") {
    globalAudioCtx.resume();
  }
  return globalAudioCtx;
}

/**
 * Robust Browser-native Speech-to-Text Fallback using Web Speech API
 */
export class BrowserSTT {
  private recognition: any = null;
  private isRunning: boolean = false;

  constructor(private onResult: (text: string, isFinal: boolean) => void, private onError: (err: string) => void) {
    if (typeof window !== "undefined") {
      const SpeechRecognition =
        (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (SpeechRecognition) {
        this.recognition = new SpeechRecognition();
        this.recognition.continuous = true;
        this.recognition.interimResults = true;
        this.recognition.maxAlternatives = 1;

        this.recognition.onresult = (event: any) => {
          let interim = "";
          let final = "";
          for (let i = event.resultIndex; i < event.results.length; ++i) {
            if (event.results[i].isFinal) {
              final += event.results[i][0].transcript;
            } else {
              interim += event.results[i][0].transcript;
            }
          }
          if (final) {
            this.onResult(final.trim(), true);
          } else if (interim) {
            this.onResult(interim.trim(), false);
          }
        };

        this.recognition.onerror = (event: any) => {
          if (event.error !== "no-speech") {
            this.onError(event.error);
          }
        };

        this.recognition.onend = () => {
          this.isRunning = false;
        };
      }
    }
  }

  start(lang: VoiceLanguage = "auto") {
    if (!this.recognition) {
      this.onError("Speech recognition not supported in this browser");
      return;
    }
    try {
      this.recognition.lang = lang === "en" ? "en-IN" : "hi-IN";
      this.recognition.start();
      this.isRunning = true;
    } catch {
      // already started or busy
    }
  }

  stop() {
    if (this.recognition && this.isRunning) {
      try {
        this.recognition.stop();
      } catch {}
      this.isRunning = false;
    }
  }
}

/**
 * Browser-native Speech Synthesis (TTS) Fallback
 */
export class BrowserTTS {
  private currentUtterance: SpeechSynthesisUtterance | null = null;
  private keepAliveInterval: any = null;

  private cleanSpeechText(raw: string): string {
    return raw
      .replace(/\*\*FACT\*\*:/gi, "Fact:")
      .replace(/\*\*INTERPRETATION\*\*:/gi, "Interpretation:")
      .replace(/\*\*RECOMMENDATION\*\*:/gi, "Recommendation:")
      .replace(/[*_#`~>]/g, " ")
      .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1") // strip markdown links
      .replace(/\s+/g, " ")
      .trim();
  }

  speak(
    text: string,
    lang: string,
    speed: number = 1.0,
    onBoundary?: (charIndex: number) => void,
    onEnd?: () => void
  ): Promise<void> {
    return new Promise((resolve) => {
      if (!isBrowserSpeechSynthesisSupported()) {
        resolve();
        return;
      }

      this.stop();

      const cleaned = this.cleanSpeechText(text);
      if (!cleaned) {
        if (onEnd) onEnd();
        resolve();
        return;
      }

      const utterance = new SpeechSynthesisUtterance(cleaned);
      this.currentUtterance = utterance;
      utterance.rate = Math.max(0.7, Math.min(1.3, speed));

      const isHindi = lang === "hi" || /[\u0900-\u097F]/.test(cleaned);
      utterance.lang = isHindi ? "hi-IN" : "en-IN";

      // Select best matching natural voice
      const selectVoice = () => {
        const voices = window.speechSynthesis.getVoices();
        if (voices && voices.length > 0) {
          const targetLangPrefix = isHindi ? "hi" : "en";
          // Prefer Indian English if en, or Hindi if hi
          const matchedVoice =
            voices.find((v) =>
              isHindi
                ? v.lang.toLowerCase().replace("_", "-").startsWith("hi")
                : v.lang.toLowerCase().replace("_", "-") === "en-in"
            ) ||
            voices.find((v) =>
              v.lang.toLowerCase().startsWith(targetLangPrefix)
            );
          if (matchedVoice) {
            utterance.voice = matchedVoice;
          }
        }
      };

      selectVoice();
      if (!utterance.voice && "onvoiceschanged" in window.speechSynthesis) {
        window.speechSynthesis.onvoiceschanged = () => {
          selectVoice();
        };
      }

      utterance.onboundary = (e) => {
        if (onBoundary) onBoundary(e.charIndex);
      };

      const handleDone = () => {
        if (this.keepAliveInterval) {
          clearInterval(this.keepAliveInterval);
          this.keepAliveInterval = null;
        }
        this.currentUtterance = null;
        if (onEnd) onEnd();
        resolve();
      };

      utterance.onend = handleDone;
      utterance.onerror = (err) => {
        console.warn("BrowserTTS utterance error:", err);
        handleDone();
      };

      // Workaround for Chrome/Edge 15s freeze bug
      this.keepAliveInterval = setInterval(() => {
        if (!window.speechSynthesis.speaking) {
          clearInterval(this.keepAliveInterval);
          this.keepAliveInterval = null;
        } else if (window.speechSynthesis.paused) {
          window.speechSynthesis.resume();
        }
      }, 5000);

      try {
        window.speechSynthesis.speak(utterance);
      } catch (e) {
        console.warn("speechSynthesis.speak error:", e);
        handleDone();
      }
    });
  }

  stop() {
    if (this.keepAliveInterval) {
      clearInterval(this.keepAliveInterval);
      this.keepAliveInterval = null;
    }
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      try {
        window.speechSynthesis.cancel();
      } catch {}
      this.currentUtterance = null;
    }
  }
}

/**
 * High-performance Audio Stream Player with Web Audio API for Gemini TTS (WAV/PCM)
 */
export class AudioPlaybackEngine {
  private audioCtx: AudioContext | null = null;
  private currentSource: AudioBufferSourceNode | null = null;
  private abortController: AbortController | null = null;
  private isMuted: boolean = false;
  private playbackRate: number = 1.0;
  private browserTts: BrowserTTS = new BrowserTTS();

  constructor() {}

  setPlaybackRate(rate: number) {
    this.playbackRate = rate;
    if (this.currentSource && (this.currentSource as any).playbackRate) {
      this.currentSource.playbackRate.value = rate;
    }
  }

  setMuted(muted: boolean) {
    this.isMuted = muted;
    if (muted) {
      this.stop();
    }
  }

  getMuted(): boolean {
    return this.isMuted;
  }

  getAbortSignal(): AbortSignal {
    if (!this.abortController || this.abortController.signal.aborted) {
      this.abortController = new AbortController();
    }
    return this.abortController.signal;
  }

  /**
   * Stop immediately (< 300 ms) for barge-in
   */
  stop() {
    if (this.abortController) {
      this.abortController.abort();
      this.abortController = new AbortController();
    }
    if (this.currentSource) {
      try {
        this.currentSource.stop(0);
        this.currentSource.disconnect();
      } catch {}
      this.currentSource = null;
    }
    this.browserTts.stop();
  }

  /**
   * Play ArrayBuffer audio (WAV container from Gemini TTS)
   */
  async playAudioBuffer(
    buffer: ArrayBuffer,
    onEnded?: () => void
  ): Promise<void> {
    if (this.isMuted) {
      if (onEnded) onEnded();
      return;
    }

    try {
      this.audioCtx = getOrCreateAudioContext();
      if (this.audioCtx.state === "suspended") {
        await this.audioCtx.resume();
      }

      // Clone array buffer for decoding safety
      const audioData = buffer.slice(0);
      const decodedBuffer = await this.audioCtx.decodeAudioData(audioData);

      // Stop previous
      if (this.currentSource) {
        try {
          this.currentSource.stop(0);
        } catch {}
      }

      const source = this.audioCtx.createBufferSource();
      source.buffer = decodedBuffer;
      source.playbackRate.value = this.playbackRate;
      source.connect(this.audioCtx.destination);
      this.currentSource = source;

      return new Promise<void>((resolve) => {
        source.onended = () => {
          this.currentSource = null;
          if (onEnded) onEnded();
          resolve();
        };
        source.start(0);
      });
    } catch (err) {
      console.warn("WebAudio playback failed, falling back to end:", err);
      if (onEnded) onEnded();
    }
  }

  /**
   * Play speech using browser TTS fallback
   */
  async playBrowserSpeech(
    text: string,
    lang: string,
    onBoundary?: (charIdx: number) => void,
    onEnded?: () => void
  ): Promise<void> {
    if (this.isMuted) {
      if (onEnded) onEnded();
      return;
    }
    await this.browserTts.speak(text, lang, this.playbackRate, onBoundary, onEnded);
  }
}
