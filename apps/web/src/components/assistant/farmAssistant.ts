/*
 * FARMLINK voice assistant: the Pilo Tech "Horizon" assistant (homeassistant/www/horizon-home.js), renamed.
 * Same bubble, Siri-like orb, wake word, follow-up conversation, "bye bye" and interruption rules; the
 * Home Assistant parts (rooms, Android, Tunisian recording through Whisper) are left out.
 * Questions go to POST /api/v1/assistant/chat with what the dashboard shows (weather, plots, advice, sensors).
 */

import { apiClient } from "@/services/apiClient";

export type AssistantLanguage = "fr" | "en" | "ar" | "ja";

/* Minimal Web Speech API types (not in the TypeScript DOM library). */
interface RecognitionAlternative { transcript: string }
interface RecognitionResult { isFinal: boolean; 0: RecognitionAlternative; length: number }
interface RecognitionEvent { resultIndex: number; results: { length: number; [i: number]: RecognitionResult } }
interface Recognition {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  onresult: ((e: RecognitionEvent) => void) | null;
  onerror: ((e: { error: string }) => void) | null;
  onend: (() => void) | null;
  start(): void;
  abort(): void;
}
type RecognitionCtor = new () => Recognition;

const DEFAULT_NAME = "Farmlink";
const PAUSE_BEFORE_SEND_MS = 1200;
const CONVERSATION_IDLE_MS = 10 * 60 * 1000;
const GOODBYE_MAX_MS = 2500;
const SPEECH_END_BASE_MS = 4000;
const SPEECH_END_MS_PER_CHAR = 120;
const INTERRUPT_MIN_WORDS = 2; // one word heard can be noise
const ECHO_SHARE = 0.6; // above this, what is heard is the assistant itself in the speakers
const GOODBYE_WORDS =
  /^(?:(?:ok|bon|merci|d'accord|ca marche|thanks|thank you)\s+)*(?:bye|bye[\s-]*bye|by|by[\s-]*by|au revoir|a bientot|a plus|stop|arrete(?:[\s-]*toi)?|c'est tout|ca suffit|goodbye|that's all|beslama|bslama|بالسلامة|بسلامة|باي|باي باي|さようなら|バイバイ)(?:\s+(?:merci|c'est tout))?$/u;

const SPEECH_LANG: Record<AssistantLanguage, string> = { fr: "fr-FR", en: "en-US", ar: "ar-TN", ja: "ja-JP" };

const TEXT: Record<AssistantLanguage, Record<string, string>> = {
  fr: { listening: "Je vous écoute", thinking: "Je réfléchis…", more: "Autre chose ?", yes: "Oui ?", goodbye: "À bientôt !",
    error: "Désolé, je n'arrive pas à joindre FARMLINK.", noMic: "Assistant vocal : utilisez Chrome ou Edge",
    allowMic: "Autorisez le micro pour parler à {name}", say: "Dites « {name} » ou touchez la bulle", touch: "Touchez la bulle pour parler",
    toggle: "Écoute « {name} » : {state}", on: "activée", off: "désactivée", tip: "Dites « bye bye » pour terminer · Parlez pour l'interrompre",
    close: "Fermer", empty: "Je n'ai pas de réponse." },
  en: { listening: "I'm listening", thinking: "Thinking…", more: "Anything else?", yes: "Yes?", goodbye: "See you soon!",
    error: "Sorry, I can't reach FARMLINK.", noMic: "Voice assistant: use Chrome or Edge",
    allowMic: "Allow the microphone to talk to {name}", say: "Say “{name}” or tap the bubble", touch: "Tap the bubble to talk",
    toggle: "Listening for “{name}”: {state}", on: "on", off: "off", tip: "Say “bye bye” to finish · Speak to interrupt",
    close: "Close", empty: "I have no answer." },
  ar: { listening: "نسمع فيك", thinking: "نخمّم…", more: "حاجة أخرى؟", yes: "نعم؟", goodbye: "بالسلامة!",
    error: "سامحني، ما نجمتش نوصل لـFARMLINK توّا.", noMic: "المساعد الصوتي: استعمل Chrome ولا Edge",
    allowMic: "اسمح بالميكرو باش تحكي مع {name}", say: "قول «{name}» ولا انقر على الفقاعة", touch: "انقر على الفقاعة باش تحكي",
    toggle: "الاستماع لـ«{name}»: {state}", on: "مفعّل", off: "موقوف", tip: "قول «باي باي» باش تكمّل · احكي باش تقطعو",
    close: "سكّر", empty: "ما عنديش جواب." },
  ja: { listening: "聞いています", thinking: "考えています…", more: "ほかに何か？", yes: "はい？", goodbye: "またね！",
    error: "FARMLINKに接続できません。", noMic: "音声アシスタント：ChromeまたはEdgeをご利用ください",
    allowMic: "{name}と話すにはマイクを許可してください", say: "「{name}」と言うか、バブルをタップ", touch: "バブルをタップして話す",
    toggle: "「{name}」の待ち受け：{state}", on: "オン", off: "オフ", tip: "「バイバイ」で終了 · 話すと中断します",
    close: "閉じる", empty: "答えがありません。" },
};

const normalizeSpeech = (text: string) => text.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
const fill = (s: string, v: Record<string, string>) => s.replace(/\{(\w+)\}/g, (_, k: string) => v[k] ?? "");

/** Wake word = the assistant's name; recognizers often split or bend "Farmlink". */
function buildWakeRe(name: string) {
  const escaped = normalizeSpeech(name).trim().replace(/[.*+?^${}()|[\]\\]/g, "\\$&").replace(/[\s-]+/g, "[\\s-]*");
  return new RegExp(
    `(?<![\\p{L}\\p{N}])(${escaped}s?|f[ae]r?m[\\s-]*l[iy]n[kc]s?|ferme[\\s-]*link|فارم[\\s-]*لينك|فارملينك|ファームリンク)(?![\\p{L}\\p{N}])`,
    "u",
  );
}

type State = "off" | "idle" | "listening" | "thinking" | "speaking" | "followup";

let contextProvider: () => Record<string, unknown> = () => ({});
/** The dashboard home publishes what it shows, so answers use the farm's live data. */
export function setAssistantContext(provider: () => Record<string, unknown>) {
  contextProvider = provider;
}

export class FarmAssistantController {
  name = DEFAULT_NAME;
  language: AssistantLanguage = "fr";
  state: State = "off";
  private wakeRe = buildWakeRe(DEFAULT_NAME);
  private wakeEnabled: boolean;
  private recognition: Recognition | null = null;
  private running = false;
  private ignoreUntil = 0;
  private stripWake = false;
  private micBlocked = false;
  private silenceTimer: ReturnType<typeof setTimeout> | undefined;
  private pauseTimer: ReturnType<typeof setTimeout> | undefined;
  private askToken = 0;
  private lastActivity = 0;
  private conversationId: string | null = null;
  private audioContext: AudioContext | null = null;
  private audio: { stream: MediaStream; frame: number; rms?: number } | null = null;
  private meterStarting: Promise<void> | null = null;
  private host: HTMLDivElement;
  private ui!: Record<"launcher" | "hint" | "overlay" | "close" | "label" | "orb" | "transcript" | "answer" | "tip" | "toggle", HTMLElement>;
  private attached = 0;
  private readonly Recognition: RecognitionCtor | undefined;

  constructor() {
    const w = window as unknown as { SpeechRecognition?: RecognitionCtor; webkitSpeechRecognition?: RecognitionCtor };
    this.Recognition = w.SpeechRecognition || w.webkitSpeechRecognition;
    try { this.wakeEnabled = localStorage.getItem("farmlink-assistant-wake") === "on"; } catch { this.wakeEnabled = false; }
    try { this.conversationId = sessionStorage.getItem("farmlink-assistant-conversation"); } catch { /* no history */ }
    this.host = document.createElement("div");
    this.host.id = "farmlink-assistant";
    this.buildUi();
  }

  private get text() { return TEXT[this.language] || TEXT.fr; }

  // --- UI (attached to document.body, above the dashboard) ----------------
  private buildUi() {
    const root = this.host.attachShadow({ mode: "open" });
    root.innerHTML = `<style>
      :host { all: initial; font-family: Inter, "Segoe UI", Roboto, system-ui, sans-serif; --accent: #4cc35a; --accent-soft: #a6e86b; --deep: #0f6b3a; }
      .launcher { position: fixed; right: 24px; bottom: 24px; z-index: 9998; width: 66px; height: 66px; border: 0; border-radius: 50%; cursor: pointer; padding: 0; background: transparent; }
      .mini { position: absolute; inset: 0; border-radius: 50%; overflow: hidden; background: #062a14; box-shadow: 0 12px 30px -8px rgba(76,195,90,.75); transition: transform .25s ease, box-shadow .25s ease; }
      .mini .blob { filter: blur(6px); animation: none; }
      .launcher:hover .mini, .launcher:focus-visible .mini { transform: scale(1.06); box-shadow: 0 14px 34px -8px rgba(166,232,107,.9); }
      .launcher:hover .mini .blob { animation: spin 6s linear infinite; }
      .launcher:focus-visible { outline: 2px solid var(--accent); outline-offset: 4px; }
      .launcher.off .mini { filter: saturate(.75); }
      .badge { position: absolute; right: 2px; top: 2px; width: 14px; height: 14px; border-radius: 50%; border: 2px solid #fff; background: #94a3b8; }
      .launcher.idle .badge { background: #22c55e; box-shadow: 0 0 0 4px rgba(34,197,94,.25); }
      .hint { position: fixed; right: 100px; bottom: 40px; z-index: 9998; padding: 8px 14px; border-radius: 999px; font-size: 13px; font-weight: 600;
        color: #17330f; background: rgba(255,255,255,.95); box-shadow: 0 10px 24px -14px rgba(15,23,42,.6); cursor: pointer;
        opacity: 0; transform: translateX(8px); transition: opacity .25s, transform .25s; white-space: nowrap; }
      .wrap:hover .hint, .hint.show { opacity: 1; transform: none; }
      .overlay { position: fixed; inset: 0; z-index: 9999; display: none; flex-direction: column; align-items: center; justify-content: center; gap: 26px;
        padding: 24px; background: radial-gradient(circle at 50% 40%, rgba(16,64,32,.78), rgba(3,14,7,.92)); backdrop-filter: blur(18px);
        -webkit-backdrop-filter: blur(18px); color: #fff; text-align: center; }
      .overlay.open { display: flex; animation: fade .25s ease; }
      .close { position: absolute; top: 22px; right: 22px; width: 44px; height: 44px; border-radius: 50%; border: 1px solid rgba(255,255,255,.25);
        background: rgba(255,255,255,.08); color: #fff; font-size: 22px; cursor: pointer; }
      .orb { position: relative; width: 240px; height: 240px; border-radius: 50%; cursor: pointer; transform: scale(var(--level, 1));
        transition: transform .08s linear; filter: drop-shadow(0 0 60px rgba(76,195,90,.55)); }
      .orb .core { position: absolute; inset: 0; border-radius: 50%; overflow: hidden; background: #052012; }
      .blob { position: absolute; inset: -20%; border-radius: 50%; mix-blend-mode: screen; filter: blur(18px); opacity: .9; will-change: transform; }
      .b1 { background: conic-gradient(from 0deg, var(--accent), #ffd54a, var(--deep), var(--accent)); animation: spin 7s linear infinite; }
      .b2 { background: radial-gradient(circle at 30% 30%, var(--accent-soft), transparent 60%), radial-gradient(circle at 70% 70%, #2bb3a3, transparent 55%); animation: spin 5s linear infinite reverse; }
      .b3 { background: radial-gradient(circle at 60% 25%, #fff59d, transparent 50%), radial-gradient(circle at 25% 75%, var(--deep), transparent 55%); animation: wobble 4s ease-in-out infinite; }
      .orb .core::after { content: ""; position: absolute; inset: 0; border-radius: 50%; opacity: 0; transition: opacity .3s ease;
        background: radial-gradient(circle at 50% 50%, rgba(239,68,68,.75), rgba(127,29,29,.4) 70%); }
      .overlay[data-state="error"] .core::after { opacity: 1; }
      .ring, .spinner, .glow { position: absolute; border-radius: 50%; pointer-events: none; opacity: 0; }
      .ring { inset: 0; border: 2px solid rgba(166,232,107,.65); }
      .overlay[data-state="listening"] .ring { animation: ripple 2.4s cubic-bezier(.2,.6,.3,1) infinite; }
      .overlay[data-state="listening"] .r2 { animation-delay: 1.2s; }
      .spinner { inset: -16px; border: 3px solid transparent; border-top-color: var(--accent-soft); border-right-color: rgba(255,213,74,.85); transition: opacity .3s ease; }
      .overlay[data-state="thinking"] .spinner { opacity: 1; animation: spin 1s linear infinite; }
      .glow { inset: -28%; background: radial-gradient(circle, rgba(166,232,107,.5), rgba(255,213,74,.18) 45%, transparent 68%); }
      .overlay[data-state="speaking"] .glow { animation: halo 1.1s ease-in-out infinite alternate; }
      @keyframes ripple { from { opacity: .75; transform: scale(1); } to { opacity: 0; transform: scale(1.6); } }
      @keyframes halo { from { opacity: .35; transform: scale(.94); } to { opacity: .9; transform: scale(1.06); } }
      .overlay[data-state="error"] .orb { animation: shake .5s ease; }
      .overlay[data-state="error"] .label { color: #fca5a5; }
      .shine { position: absolute; inset: 0; border-radius: 50%; background: radial-gradient(circle at 35% 25%, rgba(255,255,255,.55), transparent 35%); }
      .overlay[data-state="thinking"] .b1 { animation-duration: 1.6s; } .overlay[data-state="thinking"] .b2 { animation-duration: 1.2s; }
      .overlay[data-state="thinking"] .orb { animation: think 1.4s ease-in-out infinite; }
      .overlay[data-state="speaking"] .orb { animation: talk .55s ease-in-out infinite alternate; }
      .label { font-size: 15px; letter-spacing: .14em; text-transform: uppercase; color: var(--accent-soft); font-weight: 700; transition: color .3s ease; }
      .transcript { max-width: 760px; min-height: 1.3em; font-size: clamp(22px, 3.4vw, 36px); font-weight: 300; line-height: 1.3; }
      .answer { max-width: 760px; font-size: clamp(16px, 2vw, 20px); line-height: 1.5; color: #e8f5e0; white-space: pre-line; }
      .tip { font-size: 13px; color: #9fb59a; }
      .toggle { border: 1px solid rgba(255,255,255,.25); background: rgba(255,255,255,.08); color: #e2e8f0; border-radius: 999px; padding: 8px 14px; font: inherit; font-size: 13px; cursor: pointer; }
      @keyframes spin { to { transform: rotate(360deg); } }
      @keyframes wobble { 50% { transform: scale(1.18) rotate(40deg); } }
      @keyframes think { 50% { transform: scale(.92); } }
      @keyframes talk { from { transform: scale(1); } to { transform: scale(1.12); } }
      @keyframes fade { from { opacity: 0; } }
      @keyframes shake { 20%, 60% { transform: translateX(-8px); } 40%, 80% { transform: translateX(8px); } }
      @media (max-width: 600px) { .orb { width: 180px; height: 180px; } .launcher { right: 14px; bottom: 18px; width: 56px; height: 56px; } .hint { right: 80px; bottom: 30px; } }
      @media (prefers-reduced-motion: reduce) {
        .blob, .orb, .overlay.open, .mini, .ring, .glow, .spinner { animation: none !important; transition: none !important; }
        .overlay[data-state="thinking"] .spinner, .overlay[data-state="speaking"] .glow { opacity: .8; }
      }
    </style>
    <div class="wrap">
      <span class="hint" id="hint"></span>
      <button class="launcher off" id="launcher">
        <span class="mini"><span class="blob b1"></span><span class="blob b2"></span><span class="blob b3"></span><span class="shine"></span></span>
        <span class="badge"></span>
      </button>
    </div>
    <div class="overlay" id="overlay" data-state="listening" role="dialog" aria-live="polite">
      <button class="close" id="close">✕</button>
      <div class="label" id="label"></div>
      <div class="orb" id="orb"><span class="glow"></span><span class="ring r1"></span><span class="ring r2"></span><span class="spinner"></span><div class="core"><span class="blob b1"></span><span class="blob b2"></span><span class="blob b3"></span></div><span class="shine"></span></div>
      <div class="transcript" id="transcript"></div>
      <div class="answer" id="answer"></div>
      <div class="tip" id="tip"></div>
      <button class="toggle" id="toggle"></button>
    </div>`;
    const ids = ["launcher", "hint", "overlay", "close", "label", "orb", "transcript", "answer", "tip", "toggle"] as const;
    this.ui = Object.fromEntries(ids.map((id) => [id, root.getElementById(id) as HTMLElement])) as typeof this.ui;
    this.ui.launcher.addEventListener("click", () => this.openListening());
    this.ui.hint.addEventListener("click", () => this.openListening());
    this.ui.orb.addEventListener("click", () => {
      if (["followup", "speaking", "idle"].includes(this.state)) { speechSynthesis.cancel(); this.openListening(); }
    });
    this.ui.close.addEventListener("click", () => this.close());
    this.ui.toggle.addEventListener("click", () => this.setWake(!this.wakeEnabled));
    document.addEventListener("keydown", (e) => { if (e.key === "Escape" && this.ui.overlay.classList.contains("open")) this.close(); });
  }

  // --- lifecycle: active while the dashboard is shown ------------------------
  attach() {
    this.attached += 1;
    if (!this.host.isConnected) document.body.append(this.host);
    this.host.style.display = "";
    if (this.state === "off") this.state = "idle";
    this.startRecognition();
    this.refresh();
  }

  detach() {
    this.attached = Math.max(0, this.attached - 1);
    setTimeout(() => {
      if (this.attached) return;
      this.close();
      this.state = "off";
      this.stopRecognition();
      this.host.style.display = "none";
    }, 1500);
  }

  setWake(on: boolean) {
    this.wakeEnabled = on;
    try { localStorage.setItem("farmlink-assistant-wake", on ? "on" : "off"); } catch { /* storage unavailable */ }
    if (on) this.startRecognition();
    else if (!this.ui.overlay.classList.contains("open")) this.stopRecognition();
    this.refresh();
  }

  /** Listening and answering language: follows the dashboard language. */
  setLanguage(language: AssistantLanguage) {
    if (language === this.language) return;
    this.language = language;
    if (this.recognition) {
      this.stopRecognition();
      this.recognition = null;
      this.startRecognition();
    }
    this.refresh();
  }

  setName(name: string | null | undefined) {
    this.name = (name || DEFAULT_NAME).trim() || DEFAULT_NAME;
    this.wakeRe = buildWakeRe(this.name);
    this.refresh();
  }

  private refresh() {
    const supported = !!this.Recognition;
    const listeningForWake = supported && this.wakeEnabled && this.running;
    const v = { name: this.name };
    this.ui.launcher.className = `launcher ${listeningForWake ? "idle" : "off"}`;
    this.ui.launcher.title = `Assistant ${this.name}`;
    this.ui.launcher.setAttribute("aria-label", `Assistant ${this.name}`);
    this.ui.hint.textContent = !supported ? this.text.noMic : this.micBlocked ? fill(this.text.allowMic, v)
      : listeningForWake ? fill(this.text.say, v) : this.text.touch;
    this.ui.toggle.textContent = fill(this.text.toggle, { name: this.name, state: this.wakeEnabled ? this.text.on : this.text.off });
    this.ui.close.title = this.text.close;
    this.ui.overlay.dir = this.language === "ar" ? "rtl" : "ltr";
  }

  // --- speech recognition --------------------------------------------------
  private startRecognition() {
    if (!this.Recognition || this.running || !this.attached) return;
    if (!this.wakeEnabled && !this.ui.overlay.classList.contains("open")) return;
    if (!this.recognition) {
      const r = new this.Recognition();
      r.lang = SPEECH_LANG[this.language];
      r.continuous = true;
      r.interimResults = true;
      r.onresult = (event) => this.onResult(event);
      r.onerror = (event) => {
        if (event.error === "not-allowed" || event.error === "service-not-allowed") {
          this.micBlocked = true;
          this.wakeEnabled = false;
          this.refresh();
        }
      };
      r.onend = () => {
        this.running = false;
        this.ignoreUntil = 0;
        this.refresh();
        // Chrome stops listening after a silence: start again while it is useful.
        if (this.attached && (this.wakeEnabled || this.ui.overlay.classList.contains("open")) && !this.micBlocked) {
          setTimeout(() => this.startRecognition(), 300);
        }
      };
      this.recognition = r;
    }
    try {
      this.recognition.start();
      this.running = true;
      this.micBlocked = false;
    } catch { /* already started */ }
    this.refresh();
  }

  private stopRecognition() {
    this.running = false;
    try { this.recognition?.abort(); } catch { /* nothing to stop */ }
  }

  private onResult(event: RecognitionEvent) {
    let interim = "";
    let final = "";
    for (let i = Math.max(event.resultIndex, this.ignoreUntil); i < event.results.length; i += 1) {
      const text = event.results[i][0].transcript;
      if (event.results[i].isFinal) final += text; else interim += text;
    }
    const heard = (final || interim).trim();
    if (!heard) return;
    if (final && this.state !== "idle" && this.isGoodbye(final)) { void this.goodbye(); return; }
    if (this.state === "thinking" || this.state === "speaking") {
      if (!this.isInterruption(heard)) return;
      this.interrupt(event);
    }
    if (this.state === "idle") {
      if (!this.wakeRe.test(normalizeSpeech(heard))) return;
      this.ignoreUntil = Math.max(event.resultIndex, this.ignoreUntil);
      this.stripWake = true;
      this.openListening(true);
    }
    if (this.state === "listening" || this.state === "followup") {
      let text = heard;
      if (this.stripWake) {
        const match = normalizeSpeech(text).match(this.wakeRe);
        if (match && match.index !== undefined) text = text.slice(match.index + match[0].length).replace(/^[\s,.!?]+/, "");
      }
      this.state = "listening";
      this.ui.overlay.dataset.state = "listening";
      this.ui.label.textContent = this.text.listening;
      if (text) this.ui.transcript.textContent = text;
      this.ui.answer.textContent = "";
      this.armSilence();
      clearTimeout(this.pauseTimer);
      const send = () => {
        clearTimeout(this.pauseTimer);
        if (this.state !== "listening" || text.length < 2) return;
        this.ignoreUntil = event.results.length;
        this.stripWake = false;
        void this.submit(text);
      };
      if (final) send();
      else this.pauseTimer = setTimeout(send, PAUSE_BEFORE_SEND_MS);
    }
  }

  private isGoodbye(text: string) {
    let said = normalizeSpeech(text).replace(/[.,!?;:،؟。]+/g, " ").replace(/\s+/g, " ").trim();
    said = said.replace(this.wakeRe, " ").replace(/\s+/g, " ").trim();
    return GOODBYE_WORDS.test(said);
  }

  private async goodbye() {
    const token = (this.askToken += 1);
    clearTimeout(this.silenceTimer);
    clearTimeout(this.pauseTimer);
    this.state = "speaking";
    this.ui.overlay.dataset.state = "speaking";
    this.ui.label.textContent = this.name;
    this.ui.transcript.textContent = "";
    this.ui.answer.textContent = this.text.goodbye;
    await Promise.race([this.speak(this.text.goodbye), new Promise((r) => setTimeout(r, GOODBYE_MAX_MS))]);
    if (token === this.askToken && this.state === "speaking") this.close();
  }

  private isInterruption(heard: string) {
    const normalized = normalizeSpeech(heard);
    const answer = this.state === "speaking" ? this.ui.answer.textContent || "" : "";
    if (this.wakeRe.test(normalized) && !this.wakeRe.test(normalizeSpeech(answer))) return true;
    const words = normalized.split(/[^\p{L}\p{N}']+/u).filter((w) => w.length > 1);
    if (words.length < INTERRUPT_MIN_WORDS) return false;
    const said = new Set(normalizeSpeech(answer).split(/[^\p{L}\p{N}']+/u));
    return words.filter((w) => said.has(w)).length / words.length < ECHO_SHARE;
  }

  private interrupt(event: RecognitionEvent) {
    this.askToken += 1;
    speechSynthesis.cancel();
    this.ignoreUntil = event.resultIndex;
    this.stripWake = true;
    this.state = "listening";
    this.ui.overlay.dataset.state = "listening";
    this.ui.label.textContent = this.text.listening;
    this.ui.answer.textContent = "";
    this.ui.transcript.textContent = "";
  }

  private armSilence() {
    clearTimeout(this.silenceTimer);
    this.silenceTimer = setTimeout(() => {
      if (this.state === "listening" || this.state === "followup") this.close();
    }, CONVERSATION_IDLE_MS);
  }

  // --- open / close ----------------------------------------------------------
  private open() {
    this.ui.overlay.classList.add("open");
    this.ui.tip.textContent = this.text.tip;
    void this.startMeter();
    if (!this.running) this.startRecognition();
  }

  openListening(fromWake = false) {
    if (!this.Recognition) {
      this.ui.hint.classList.add("show");
      setTimeout(() => this.ui.hint.classList.remove("show"), 3000);
      return;
    }
    speechSynthesis.cancel();
    this.lastActivity = Date.now();
    this.state = "listening";
    this.ui.overlay.dataset.state = "listening";
    this.ui.label.textContent = this.text.listening;
    this.ui.transcript.textContent = fromWake ? this.text.yes : "";
    this.ui.answer.textContent = "";
    this.open();
    this.chime();
    this.armSilence();
  }

  close() {
    clearTimeout(this.silenceTimer);
    clearTimeout(this.pauseTimer);
    speechSynthesis.cancel();
    this.ui.overlay.classList.remove("open");
    this.stopMeter();
    if (this.state !== "off") this.state = "idle";
    if (!this.wakeEnabled) this.stopRecognition();
    this.refresh();
  }

  /** A typed question (dashboard card): same bubble, same answer, read aloud. */
  async askTyped(text: string): Promise<string> {
    this.open();
    return this.submit(text);
  }

  // --- question to the backend and spoken answer --------------------------------
  private async submit(text: string): Promise<string> {
    clearTimeout(this.silenceTimer);
    clearTimeout(this.pauseTimer);
    if (this.isGoodbye(text)) { void this.goodbye(); return this.text.goodbye; }
    this.lastActivity = Date.now();
    this.state = "thinking";
    this.ui.overlay.dataset.state = "thinking";
    this.ui.label.textContent = this.text.thinking;
    this.ui.transcript.textContent = text;
    this.ui.answer.textContent = "";
    const token = (this.askToken += 1);
    let answer: string;
    let failed = false;
    try {
      answer = await this.ask(text);
    } catch {
      answer = this.text.error;
      failed = true;
    }
    if (this.state !== "thinking" || token !== this.askToken) return answer;
    this.state = "speaking";
    this.ui.overlay.dataset.state = failed ? "error" : "speaking";
    this.ui.label.textContent = this.name;
    this.ui.answer.textContent = answer;
    await this.speak(answer);
    if (failed) await new Promise((r) => setTimeout(r, 1500));
    if (this.state !== "speaking" || token !== this.askToken) return answer;
    // Follow-up without saying the name again.
    this.state = "followup";
    this.ui.overlay.dataset.state = "listening";
    this.ui.label.textContent = this.text.more;
    this.ignoreUntil = Number.MAX_SAFE_INTEGER;
    this.stopRecognition();
    setTimeout(() => { this.ignoreUntil = 0; this.startRecognition(); }, 250);
    this.armSilence();
    return answer;
  }

  private async ask(text: string): Promise<string> {
    let context: Record<string, unknown> = {};
    try { context = contextProvider(); } catch { /* no page data */ }
    const body = await apiClient<{ message: string; conversation_id: string; assistant_name: string }>("/assistant/chat", {
      method: "POST",
      body: JSON.stringify({ message: text, language: this.language, conversation_id: this.conversationId, context }),
    });
    this.conversationId = body.conversation_id;
    try { sessionStorage.setItem("farmlink-assistant-conversation", body.conversation_id); } catch { /* no history */ }
    if (body.assistant_name && body.assistant_name !== this.name) this.setName(body.assistant_name);
    return body.message || this.text.empty;
  }

  private speak(text: string): Promise<void> {
    return new Promise((resolve) => {
      if (!("speechSynthesis" in window)) { resolve(); return; }
      const spoken = text.replace(/[*_`#>]/g, "").replace(/\s+/g, " ").trim().slice(0, 400);
      const utterance = new SpeechSynthesisUtterance(spoken || text);
      const lang = SPEECH_LANG[this.language];
      utterance.lang = lang;
      const voices = speechSynthesis.getVoices().filter((v) => v.lang.startsWith(lang.slice(0, 2)));
      utterance.voice = voices.find((v) => v.lang === lang && /natural|online|google/i.test(v.name))
        || voices.find((v) => /natural|online|google|denise|henri|eloise/i.test(v.name)) || voices[0] || null;
      utterance.rate = 1.03;
      const limit = setTimeout(resolve, SPEECH_END_BASE_MS + (spoken || text).length * SPEECH_END_MS_PER_CHAR);
      const finished = () => { clearTimeout(limit); resolve(); };
      utterance.onend = finished;
      utterance.onerror = finished;
      speechSynthesis.cancel();
      speechSynthesis.resume?.();
      speechSynthesis.speak(utterance);
    });
  }

  // --- effects: wake chime and an orb that follows the voice ----------------------
  private chime() {
    try {
      const ctx = this.audioContext || (this.audioContext = new AudioContext());
      const now = ctx.currentTime;
      [880, 1320].forEach((freq, i) => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.frequency.value = freq;
        gain.gain.setValueAtTime(0.0001, now + i * 0.09);
        gain.gain.exponentialRampToValueAtTime(0.12, now + i * 0.09 + 0.02);
        gain.gain.exponentialRampToValueAtTime(0.0001, now + i * 0.09 + 0.22);
        osc.connect(gain).connect(ctx.destination);
        osc.start(now + i * 0.09);
        osc.stop(now + i * 0.09 + 0.25);
      });
    } catch { /* audio unavailable */ }
  }

  private async startMeter() {
    if (this.audio) return;
    if (this.meterStarting) return this.meterStarting;
    this.meterStarting = this.openMeter().finally(() => { this.meterStarting = null; });
    return this.meterStarting;
  }

  private async openMeter() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const ctx = this.audioContext || (this.audioContext = new AudioContext());
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 512;
      ctx.createMediaStreamSource(stream).connect(analyser);
      const data = new Uint8Array(analyser.fftSize);
      this.audio = { stream, frame: 0 };
      const tick = () => {
        if (!this.audio) return;
        analyser.getByteTimeDomainData(data);
        let sum = 0;
        for (const v of data) sum += ((v - 128) / 128) ** 2;
        this.audio.rms = Math.sqrt(sum / data.length);
        const level = Math.min(1.35, 1 + this.audio.rms * 3);
        if (this.state === "listening" || this.state === "followup") this.ui.orb.style.setProperty("--level", level.toFixed(3));
        else this.ui.orb.style.removeProperty("--level");
        this.audio.frame = requestAnimationFrame(tick);
      };
      tick();
    } catch { /* microphone refused: the orb stays animated without following the voice */ }
  }

  private stopMeter() {
    if (!this.audio) return;
    cancelAnimationFrame(this.audio.frame);
    this.audio.stream.getTracks().forEach((t) => t.stop());
    this.audio = null;
    this.ui.orb.style.removeProperty("--level");
  }
}

let controller: FarmAssistantController | null = null;
/** One assistant for the whole dashboard. */
export function getAssistant(): FarmAssistantController {
  if (!controller) controller = new FarmAssistantController();
  return controller;
}
