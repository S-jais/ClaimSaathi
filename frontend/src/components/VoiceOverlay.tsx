"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  VoiceState,
  VoiceLanguage,
  BrowserSTT,
  AudioPlaybackEngine,
  getSupportedAudioMimeType,
  getOrCreateAudioContext,
} from "@/lib/voice";
import { voiceApi, type VoiceConfigData } from "@/lib/api";
import { useLanguage } from "@/context/LanguageContext";

interface VoiceOverlayProps {
  isOpen: boolean;
  onClose: () => void;
  onSendVoiceMessage: (
    text: string,
    lang: VoiceLanguage,
    confidence?: number
  ) => Promise<{ reply: string; spoken_text?: string; language?: string; read_back_required?: boolean }>;
  onFallbackToText: () => void;
}

export default function VoiceOverlay({
  isOpen,
  onClose,
  onSendVoiceMessage,
  onFallbackToText,
}: VoiceOverlayProps) {
  const { lang: appLang, t } = useLanguage();

  const [state, setState] = useState<VoiceState>("IDLE");
  const [selectedLang, setSelectedLang] = useState<VoiceLanguage>("auto");
  const [speed, setSpeed] = useState<number>(1.0);
  const [isMuted, setIsMuted] = useState<boolean>(false);
  const [audioLevel, setAudioLevel] = useState<number>(0);

  // Transcript & Captions
  const [transcript, setTranscript] = useState<string>("");
  const transcriptRef = useRef<string>("");
  const [spokenCaption, setSpokenCaption] = useState<string>("");
  const [activeSentenceIndex, setActiveSentenceIndex] = useState<number>(0);
  const [sentences, setSentences] = useState<string[]>([]);
  const [readBackConfirmation, setReadBackConfirmation] = useState<{
    text: string;
    required: boolean;
  } | null>(null);

  // Audio recording & Web Audio
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  // Audio Playback Engine
  const playbackEngineRef = useRef<AudioPlaybackEngine | null>(null);
  const browserSttRef = useRef<BrowserSTT | null>(null);

  // Silence VAD & Auto-Stop
  const silenceTimerRef = useRef<NodeJS.Timeout | null>(null);
  const recordingTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const hasSpokenRef = useRef<boolean>(false);
  const isClosingRef = useRef<boolean>(false);

  // Init Playback Engine
  useEffect(() => {
    playbackEngineRef.current = new AudioPlaybackEngine();
    return () => {
      playbackEngineRef.current?.stop();
    };
  }, []);

  // Update speed & mute
  useEffect(() => {
    playbackEngineRef.current?.setPlaybackRate(speed);
  }, [speed]);

  useEffect(() => {
    playbackEngineRef.current?.setMuted(isMuted);
  }, [isMuted]);

  // Clean up on unmount or close
  const cleanupRecording = useCallback(() => {
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }
    if (recordingTimeoutRef.current) {
      clearTimeout(recordingTimeoutRef.current);
      recordingTimeoutRef.current = null;
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      try {
        mediaRecorderRef.current.stop();
      } catch {}
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    browserSttRef.current?.stop();
    setAudioLevel(0);
  }, []);

  // Barge-in: immediately stop playback and start listening
  const handleBargeIn = useCallback(() => {
    if (state === "SPEAKING") {
      playbackEngineRef.current?.stop();
      setState("IDLE");
      startListening();
    }
  }, [state]);

  // Auto-start listening on open
  useEffect(() => {
    if (isOpen) {
      isClosingRef.current = false;
      const timer = setTimeout(() => {
        if (!isClosingRef.current) {
          startListening();
        }
      }, 250);
      return () => clearTimeout(timer);
    } else {
      isClosingRef.current = true;
      cleanupRecording();
      playbackEngineRef.current?.stop();
      setState("IDLE");
      setTranscript("");
      transcriptRef.current = "";
      hasSpokenRef.current = false;
      setSpokenCaption("");
      setReadBackConfirmation(null);
    }
  }, [isOpen, cleanupRecording]);

  // Start capture flow
  const startListening = async () => {
    if (isClosingRef.current) return;
    // If speaking, barge-in immediately
    if (state === "SPEAKING") {
      playbackEngineRef.current?.stop();
    }

    try {
      cleanupRecording();
      setTranscript("");
      transcriptRef.current = "";
      hasSpokenRef.current = false;
      setReadBackConfirmation(null);

      // Request mic
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
      streamRef.current = stream;

      // Setup audio analyzer for level meter
      const audioCtx = getOrCreateAudioContext();
      if (audioCtx.state === "suspended") {
        await audioCtx.resume();
      }
      const source = audioCtx.createMediaStreamSource(stream);
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 64;
      analyser.smoothingTimeConstant = 0.4;
      source.connect(analyser);
      analyserRef.current = analyser;

      // Level meter & VAD loop
      const dataArray = new Uint8Array(analyser.frequencyBinCount);
      const updateLevel = () => {
        if (!analyserRef.current) return;
        analyserRef.current.getByteFrequencyData(dataArray);
        let sum = 0;
        for (let i = 0; i < dataArray.length; i++) {
          sum += dataArray[i];
        }
        const avg = sum / dataArray.length;
        const normalized = Math.min(1.0, avg / 128);
        setAudioLevel(normalized);

        // Real-time Energy VAD for silence detection
        if (normalized > 0.14) {
          hasSpokenRef.current = true;
          if (silenceTimerRef.current) {
            clearTimeout(silenceTimerRef.current);
            silenceTimerRef.current = null;
          }
        } else if (hasSpokenRef.current && normalized < 0.08) {
          if (!silenceTimerRef.current) {
            silenceTimerRef.current = setTimeout(() => {
              stopListening();
            }, 1400); // 1.4s of quiet after speaking auto-submits
          }
        }
        animationFrameRef.current = requestAnimationFrame(updateLevel);
      };
      updateLevel();

      // Setup MediaRecorder
      const mimeType = getSupportedAudioMimeType();
      audioChunksRef.current = [];
      const options = mimeType ? { mimeType } : undefined;
      const mediaRecorder = new MediaRecorder(stream, options);
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) {
          audioChunksRef.current.push(e.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, {
          type: mimeType || "audio/webm",
        });
        const currentText = transcriptRef.current.trim();
        if (audioBlob.size > 1000 || currentText.length > 0) {
          await processRecordedAudio(audioBlob);
        } else {
          setState("IDLE");
        }
      };

      mediaRecorder.start(250);
      setState("LISTENING");

      // Auto-stop after 30 seconds max
      recordingTimeoutRef.current = setTimeout(() => {
        stopListening();
      }, 30000);

      // Browser STT parallel fallback for real-time live captions & fast VAD
      browserSttRef.current = new BrowserSTT(
        (text, isFinal) => {
          if (text) {
            hasSpokenRef.current = true;
            setTranscript(text);
            transcriptRef.current = text;
            if (isFinal) {
              if (silenceTimerRef.current) {
                clearTimeout(silenceTimerRef.current);
              }
              silenceTimerRef.current = setTimeout(() => {
                stopListening();
              }, 1100);
            }
          }
        },
        (err) => {
          // background errors ignored
        }
      );
      browserSttRef.current.start(selectedLang);
    } catch (err: any) {
      console.warn("Microphone access error:", err);
      if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
        setState("PERMISSION_DENIED");
      } else {
        setState("ERROR");
      }
    }
  };

  const stopListening = () => {
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }
    cleanupRecording();
    setState("TRANSCRIBING");
  };

  // Process recorded audio through Backend Gemini STT -> Orchestrator -> TTS
  const processRecordedAudio = async (audioBlob: Blob) => {
    setState("TRANSCRIBING");

    let finalTranscript = transcriptRef.current.trim();
    let detectedLang = selectedLang === "auto" ? "hi" : selectedLang;
    let confidence = 0.95;

    // 1. Try Backend Gemini STT
    try {
      const sttRes = await voiceApi.transcribe(
        audioBlob,
        selectedLang === "auto" ? undefined : selectedLang
      );
      if (sttRes && sttRes.text && sttRes.text.trim()) {
        finalTranscript = sttRes.text.trim();
        detectedLang = (sttRes.language as any) || detectedLang;
        confidence = sttRes.confidence;
        setTranscript(finalTranscript);
        transcriptRef.current = finalTranscript;
      }
    } catch (err) {
      console.info("Gemini STT unavailable, using client speech transcript:", err);
    }

    if (!finalTranscript) {
      setState("IDLE");
      return;
    }

    // 2. Pass to Copilot Orchestrator (Mode = voice)
    setState("THINKING");
    try {
      const copilotResponse = await onSendVoiceMessage(
        finalTranscript,
        selectedLang,
        confidence
      );

      const spoken = copilotResponse.spoken_text || copilotResponse.reply;
      setSpokenCaption(spoken);

      // Split into sentence chunks for synchronized captions
      const parsedSentences = spoken
        .split(/(?<=[।?!.])\s+/)
        .filter((s) => s.trim().length > 0);
      setSentences(parsedSentences);
      setActiveSentenceIndex(0);

      // Check if read-back confirmation is required
      if (copilotResponse.read_back_required) {
        setReadBackConfirmation({
          text: finalTranscript,
          required: true,
        });
      }

      // 3. Play audio response (Gemini TTS with Browser fallback)
      await playResponseSpeech(spoken, copilotResponse.language || detectedLang);
    } catch (err) {
      console.error("Voice turn processing error:", err);
      setState("ERROR");
    }
  };

  // Play audio response using Gemini TTS with graceful browser fallback
  const playResponseSpeech = async (text: string, language: string) => {
    if (!playbackEngineRef.current) return;
    setState("SPEAKING");

    const signal = playbackEngineRef.current.getAbortSignal();

    const onPlaybackComplete = () => {
      setState("IDLE");
      // Auto-restart listening after assistant completes speech for seamless dialog
      setTimeout(() => {
        if (!isClosingRef.current) {
          startListening();
        }
      }, 500);
    };

    try {
      // Tier 1: Gemini TTS
      const audioArrayBuffer = await voiceApi.speak(
        text,
        language,
        undefined,
        speed,
        signal
      );

      if (audioArrayBuffer && audioArrayBuffer.byteLength > 1000) {
        await playbackEngineRef.current.playAudioBuffer(audioArrayBuffer, onPlaybackComplete);
        return;
      }
    } catch (err: any) {
      if (signal.aborted) {
        // Barge-in occurred
        return;
      }
      console.info("Tier 1 Gemini TTS unavailable, using Tier 2 BrowserTTS:", err);
    }

    // Tier 2: Browser Speech Synthesis Fallback (Natively speaks Hindi & English)
    try {
      await playbackEngineRef.current.playBrowserSpeech(
        text,
        language,
        (charIndex) => {
          let accumulated = 0;
          for (let i = 0; i < sentences.length; i++) {
            accumulated += sentences[i].length + 1;
            if (charIndex < accumulated) {
              setActiveSentenceIndex(i);
              break;
            }
          }
        },
        onPlaybackComplete
      );
    } catch (err) {
      console.error("Browser TTS fallback failed:", err);
      setState("IDLE");
    }
  };

  // Replay last spoken answer
  const handleReplay = () => {
    if (spokenCaption) {
      playResponseSpeech(spokenCaption, selectedLang === "en" ? "en" : "hi");
    }
  };

  if (!isOpen) return null;

  return (
    <div
      className="voice-overlay-backdrop"
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 1200,
        background: "rgba(11, 15, 25, 0.88)",
        backdropFilter: "blur(16px)",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "2rem 1.5rem",
        color: "#ffffff",
      }}
      role="dialog"
      aria-modal="true"
      aria-label="Voice Conversation Mode"
    >
      {/* Top Header Controls */}
      <div
        style={{
          width: "100%",
          maxWidth: 640,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        {/* Language Switcher Chips */}
        <div style={{ display: "flex", gap: "0.4rem", background: "rgba(255,255,255,0.06)", padding: "0.25rem", borderRadius: "20px" }}>
          {(["auto", "hi", "en"] as VoiceLanguage[]).map((l) => (
            <button
              key={l}
              onClick={() => setSelectedLang(l)}
              style={{
                background: selectedLang === l ? "var(--mistral-amber, #f97316)" : "transparent",
                color: selectedLang === l ? "#000" : "#cbd5e1",
                border: "none",
                borderRadius: "16px",
                padding: "0.3rem 0.8rem",
                fontSize: "0.78rem",
                fontWeight: 600,
                cursor: "pointer",
                transition: "all 0.2s ease",
              }}
            >
              {l === "auto" ? t("voice.chipAuto", "Auto") : l === "hi" ? t("voice.chipHi", "हिन्दी") : t("voice.chipEn", "English")}
            </button>
          ))}
        </div>

        {/* Action buttons: Speed, Mute, Close */}
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          {/* Speed Toggle */}
          <button
            onClick={() => setSpeed((prev) => (prev === 1.0 ? 1.2 : prev === 1.2 ? 0.8 : 1.0))}
            style={{
              background: "rgba(255,255,255,0.08)",
              border: "1px solid rgba(255,255,255,0.15)",
              color: "#f8fafc",
              padding: "0.35rem 0.65rem",
              borderRadius: "8px",
              fontSize: "0.75rem",
              fontFamily: "var(--font-mono, monospace)",
              cursor: "pointer",
            }}
            title="Speech Speed"
          >
            {speed.toFixed(1)}×
          </button>

          {/* Mute Toggle */}
          <button
            onClick={() => setIsMuted((m) => !m)}
            style={{
              background: isMuted ? "rgba(239, 68, 68, 0.25)" : "rgba(255,255,255,0.08)",
              border: "1px solid rgba(255,255,255,0.15)",
              color: isMuted ? "#f87171" : "#f8fafc",
              padding: "0.35rem 0.65rem",
              borderRadius: "8px",
              fontSize: "0.75rem",
              cursor: "pointer",
            }}
            title={isMuted ? t("voice.unmute", "Unmute") : t("voice.mute", "Mute")}
          >
            {isMuted ? "🔇" : "🔊"}
          </button>

          {/* Exit / Type Instead */}
          <button
            onClick={() => {
              cleanupRecording();
              playbackEngineRef.current?.stop();
              onFallbackToText();
            }}
            style={{
              background: "rgba(255,255,255,0.08)",
              border: "1px solid rgba(255,255,255,0.15)",
              color: "#cbd5e1",
              padding: "0.35rem 0.75rem",
              borderRadius: "8px",
              fontSize: "0.75rem",
              cursor: "pointer",
            }}
          >
            {t("voice.typeInstead", "Type instead")}
          </button>

          <button
            onClick={onClose}
            style={{
              background: "transparent",
              border: "none",
              color: "#94a3b8",
              fontSize: "1.4rem",
              cursor: "pointer",
              padding: "0 0.4rem",
            }}
            aria-label="Close Voice Mode"
          >
            ✕
          </button>
        </div>
      </div>

      {/* Center Dynamic Visualizer & Captions */}
      <div
        style={{
          width: "100%",
          maxWidth: 680,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          textAlign: "center",
          gap: "1.8rem",
          margin: "auto 0",
        }}
      >
        {/* Pulsing Voice Orb / Mic Button */}
        <div style={{ position: "relative", display: "flex", alignItems: "center", justifyContent: "center" }}>
          {/* Animated glow ring */}
          <div
            style={{
              position: "absolute",
              width: 140 + audioLevel * 70,
              height: 140 + audioLevel * 70,
              borderRadius: "50%",
              background:
                state === "LISTENING"
                  ? "radial-gradient(circle, rgba(249, 115, 22, 0.4) 0%, rgba(249, 115, 22, 0) 70%)"
                  : state === "SPEAKING"
                  ? "radial-gradient(circle, rgba(56, 189, 248, 0.4) 0%, rgba(56, 189, 248, 0) 70%)"
                  : state === "THINKING"
                  ? "radial-gradient(circle, rgba(168, 85, 247, 0.4) 0%, rgba(168, 85, 247, 0) 70%)"
                  : "transparent",
              transition: "all 0.15s ease-out",
              pointerEvents: "none",
            }}
          />

          <button
            onClick={() => {
              if (state === "IDLE" || state === "ERROR" || state === "PERMISSION_DENIED") {
                startListening();
              } else if (state === "LISTENING") {
                stopListening();
              } else if (state === "SPEAKING") {
                handleBargeIn();
              }
            }}
            style={{
              width: 110,
              height: 110,
              borderRadius: "50%",
              background:
                state === "LISTENING"
                  ? "linear-gradient(135deg, #ea580c, #c2410c)"
                  : state === "SPEAKING"
                  ? "linear-gradient(135deg, #0284c7, #0369a1)"
                  : state === "THINKING"
                  ? "linear-gradient(135deg, #7e22ce, #6b21a8)"
                  : "linear-gradient(135deg, #1e293b, #0f172a)",
              border: "2px solid rgba(255, 255, 255, 0.2)",
              boxShadow: "0 8px 32px rgba(0, 0, 0, 0.5)",
              color: "#ffffff",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              cursor: "pointer",
              position: "relative",
              zIndex: 2,
              transform: state === "LISTENING" ? `scale(${1 + audioLevel * 0.15})` : "scale(1)",
              transition: "transform 0.1s ease, background 0.3s ease",
            }}
            aria-label={state === "LISTENING" ? "Stop listening" : "Start speaking"}
          >
            {state === "LISTENING" ? (
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="6" y="6" width="12" height="12" rx="2" fill="currentColor" />
              </svg>
            ) : state === "SPEAKING" ? (
              <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                <span style={{ width: 4, height: 24, background: "#fff", borderRadius: 2, animation: "bounce 0.6s infinite alternate" }} />
                <span style={{ width: 4, height: 34, background: "#fff", borderRadius: 2, animation: "bounce 0.6s infinite alternate 0.2s" }} />
                <span style={{ width: 4, height: 18, background: "#fff", borderRadius: 2, animation: "bounce 0.6s infinite alternate 0.4s" }} />
              </div>
            ) : state === "THINKING" ? (
              <div style={{ width: 32, height: 32, border: "3px solid #fff", borderTopColor: "transparent", borderRadius: "50%", animation: "spin 0.8s linear infinite" }} />
            ) : (
              <svg width="42" height="42" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
                <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
                <line x1="12" y1="19" x2="12" y2="23" />
                <line x1="8" y1="23" x2="16" y2="23" />
              </svg>
            )}
          </button>
        </div>

        {/* State Label */}
        <div>
          <span
            style={{
              fontFamily: "var(--font-mono, monospace)",
              fontSize: "0.85rem",
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              color:
                state === "LISTENING"
                  ? "var(--mistral-amber, #f97316)"
                  : state === "SPEAKING"
                  ? "#38bdf8"
                  : state === "THINKING"
                  ? "#c084fc"
                  : "#94a3b8",
            }}
          >
            {state === "IDLE" && t("voice.state.idle", "Tap mic to speak")}
            {state === "LISTENING" && t("voice.state.listening", "Listening... tap to send")}
            {state === "TRANSCRIBING" && t("voice.state.transcribing", "Recognizing speech...")}
            {state === "THINKING" && t("voice.state.thinking", "Consulting claim evidence...")}
            {state === "SPEAKING" && t("voice.state.speaking", "Speaking... tap mic to interrupt")}
            {state === "PERMISSION_DENIED" && t("voice.state.permissionDenied", "Microphone access denied")}
            {state === "ERROR" && t("voice.state.error", "Voice service error")}
          </span>
        </div>

        {/* Captions Display (Synchronized) */}
        <div
          style={{
            minHeight: 90,
            maxWidth: 580,
            padding: "1rem 1.25rem",
            borderRadius: "12px",
            background: "rgba(255, 255, 255, 0.04)",
            border: "1px solid rgba(255, 255, 255, 0.08)",
            fontSize: "1.05rem",
            lineHeight: 1.6,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
          }}
          aria-live="polite"
        >
          {state === "LISTENING" && (
            <p style={{ color: "#f1f5f9", fontStyle: "italic", margin: 0 }}>
              &ldquo;{transcript || "Listening for your question in Hindi, English, or Hinglish..."}&rdquo;
            </p>
          )}

          {state === "SPEAKING" && (
            <div style={{ color: "#f8fafc", margin: 0 }}>
              {sentences.length > 0 ? (
                sentences.map((s, idx) => (
                  <span
                    key={idx}
                    style={{
                      background:
                        idx === activeSentenceIndex ? "rgba(56, 189, 248, 0.25)" : "transparent",
                      color: idx === activeSentenceIndex ? "#ffffff" : "#94a3b8",
                      borderRadius: "4px",
                      padding: "0 3px",
                      transition: "all 0.2s ease",
                    }}
                  >
                    {s}{" "}
                  </span>
                ))
              ) : (
                <span>{spokenCaption}</span>
              )}
            </div>
          )}

          {state === "IDLE" && spokenCaption && (
            <div style={{ color: "#e2e8f0" }}>
              <span>{spokenCaption}</span>
              <div style={{ marginTop: "0.8rem", display: "flex", gap: "0.6rem", justifyContent: "center" }}>
                <button
                  onClick={handleReplay}
                  style={{
                    background: "rgba(255,255,255,0.08)",
                    border: "1px solid rgba(255,255,255,0.15)",
                    color: "#f1f5f9",
                    borderRadius: "6px",
                    padding: "0.3rem 0.75rem",
                    fontSize: "0.8rem",
                    cursor: "pointer",
                  }}
                >
                  ↻ {t("voice.replay", "Replay")}
                </button>
              </div>
            </div>
          )}

          {/* Read-Back Verification Chips */}
          {readBackConfirmation && (
            <div
              style={{
                marginTop: "1rem",
                padding: "0.75rem",
                borderRadius: "8px",
                background: "rgba(249, 115, 22, 0.15)",
                border: "1px solid rgba(249, 115, 22, 0.3)",
              }}
            >
              <div style={{ fontSize: "0.85rem", color: "#fdba74", marginBottom: "0.5rem" }}>
                {t("voice.confirmHeading", "Heard:")} <strong>&ldquo;{readBackConfirmation.text}&rdquo;</strong>
              </div>
              <div style={{ display: "flex", gap: "0.5rem", justifyContent: "center" }}>
                <button
                  onClick={() => setReadBackConfirmation(null)}
                  style={{
                    background: "var(--mistral-amber, #f97316)",
                    color: "#000",
                    border: "none",
                    borderRadius: "6px",
                    padding: "0.3rem 0.8rem",
                    fontSize: "0.8rem",
                    fontWeight: 700,
                    cursor: "pointer",
                  }}
                >
                  {t("voice.confirmYes", "हाँ (Correct)")}
                </button>
                <button
                  onClick={() => {
                    setReadBackConfirmation(null);
                    startListening();
                  }}
                  style={{
                    background: "rgba(255,255,255,0.1)",
                    color: "#fff",
                    border: "none",
                    borderRadius: "6px",
                    padding: "0.3rem 0.8rem",
                    fontSize: "0.8rem",
                    cursor: "pointer",
                  }}
                >
                  {t("voice.confirmNo", "नहीं (Retry)")}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Bottom Privacy & Human Approval Notice */}
      <div
        style={{
          width: "100%",
          maxWidth: 640,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          textAlign: "center",
          gap: "0.4rem",
        }}
      >
        <span
          style={{
            fontSize: "0.75rem",
            color: "#94a3b8",
            display: "flex",
            alignItems: "center",
            gap: "0.4rem",
          }}
        >
          🔒 {t("voice.consentNotice", "Audio processed in-memory for real-time guidance. Recordings are never stored.")}
        </span>
        <span
          style={{
            fontSize: "0.7rem",
            color: "#64748b",
          }}
        >
          {t("voice.draftNotice", "Drafts can be reviewed aloud, but sending strictly requires an on-screen tap.")}
        </span>
      </div>
    </div>
  );
}
