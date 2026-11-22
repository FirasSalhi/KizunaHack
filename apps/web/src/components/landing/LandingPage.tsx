"use client";

import Lenis from "lenis";
import Image from "next/image";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { PLATE } from "./plateData";
import { buildCropRow, buildRootContinuation, buildShrub } from "./rootSystem";
import { BrandLogo } from "@/components/BrandLogo";
import { BrandMark, IconTrendDown } from "@/components/icons";
import { InstallBanner, InstallButton } from "@/components/pwa/InstallApp";
import { LanguageSwitcher } from "@/i18n/LanguageSwitcher";
import { Lines, useI18n } from "@/i18n/I18nProvider";

const CONTINUATION = buildRootContinuation(PLATE.tips);
const CROPS = buildCropRow();
const SHRUB = buildShrub();

/* ---------- Top Navigation ---------- */

function LandingNav() {
  const { m } = useI18n();
  return (
    <header className="site-nav">
      <Link href="/" className="site-nav-logo" aria-label={m.common.home}><BrandLogo size={42} className="rounded-[10px]" /></Link>
      <LanguageSwitcher className="site-nav-lang" />
      <InstallButton className="site-nav-install" />
      <Link href="/login" className="site-nav-signin" aria-label={m.auth.signInLink}>
        <span className="signin-dot" aria-hidden="true" />
        <span>{m.common.signIn}</span>
        <svg className="signin-arrow" viewBox="0 0 12 12" fill="none" aria-hidden="true">
          <path d="M4.5 2.5L8 6L4.5 9.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </Link>
    </header>
  );
}

/* ---------- small shared pieces ---------- */

function Mark({ children }: { children: React.ReactNode }) {
  return (
    <span className="mark">
      <span className="mark-icon" aria-hidden="true"><BrandMark /></span>
      {children}
    </span>
  );
}

function DemoButton({ children, href = "/signup", className = "" }: { children?: React.ReactNode; href?: string; className?: string }) {
  const { m } = useI18n();
  return (
    <Link className={`demo-btn ${className}`.trim()} href={href}>
      {children ?? m.common.getStarted}
      <span aria-hidden="true" className="demo-btn-arrow">›</span>
    </Link>
  );
}

function ScrollHint() {
  const { m } = useI18n();
  return (
    <span className="scroll-hint">
      <svg viewBox="0 0 12 16" aria-hidden="true"><path d="M6 1 2 5h8L6 1Zm0 14 4-4H2l4 4Z" /></svg>
      {m.common.scrollToExplore}
    </span>
  );
}

function Photo({ src, alt, sizes = "100vw", priority = false, className }: { src: string; alt: string; sizes?: string; priority?: boolean; className?: string }) {
  return <Image src={src} alt={alt} fill sizes={sizes} priority={priority} className={className} />;
}

function Brackets() {
  return (
    <>
      <i className="bracket bracket--tl" aria-hidden="true" />
      <i className="bracket bracket--tr" aria-hidden="true" />
      <i className="bracket bracket--bl" aria-hidden="true" />
      <i className="bracket bracket--br" aria-hidden="true" />
    </>
  );
}

/* ---------- 0. Hero: the two supplied frames (hand + seedling → "Grow more. Water less.") ---------- */

function Hero() {
  const { m } = useI18n();
  const sectionRef = useRef<HTMLElement>(null);
  const mediaRef = useRef<HTMLDivElement>(null);
  const introRef = useRef<HTMLVideoElement>(null);
  const loopRef = useRef<HTMLVideoElement>(null);
  const plateRef = useRef<HTMLVideoElement>(null);
  const [looping, setLooping] = useState(false);

  useEffect(() => {
    const section = sectionRef.current;
    const media = mediaRef.current;
    const intro = introRef.current;
    const loop = loopRef.current;
    const plate = plateRef.current;
    if (!section || !media || !intro || !loop || !plate) return;
    const reduced = typeof window.matchMedia === "function" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!reduced) void intro.play()?.catch(() => undefined);
    else intro.pause();

    // Prime the plate so it can be seeked on every browser (iOS only buffers a video after a play).
    void plate.play()?.then(() => plate.pause()).catch(() => undefined);

    // Seek the plate without flooding the decoder: one seek in flight, always to the latest target.
    let target = 0;
    let pending = false;
    const seek = () => {
      if (plate.seeking) {
        pending = true;
        return;
      }
      if (Math.abs(plate.currentTime - target) > 0.004) plate.currentTime = target;
    };
    const onSeeked = () => {
      if (pending) {
        pending = false;
        seek();
      }
    };
    plate.addEventListener("seeked", onSeeked);

    const last = PLATE.frames - 1;
    const uiLayers = Array.from(section.querySelectorAll<HTMLElement>(".hero-ui, .hero-ui-media"));
    const rootsSvg = section.querySelector<SVGSVGElement>(".root-continue");
    const caption = section.querySelector<HTMLElement>(".hero-caption");

    // Layout is measured once (and on resize), never inside the scroll handler.
    let top = 0;
    let travel = 1;
    let mediaHeight = 1;
    const measure = () => {
      top = section.getBoundingClientRect().top + window.scrollY;
      travel = Math.max(1, section.offsetHeight - window.innerHeight);
      mediaHeight = media.offsetHeight;
    };

    // Each value is written to the one element that uses it, and only when it changes.
    let lastUi = Number.NaN;
    let lastR = -1;
    let lastQ = -1;
    let lastPhase = "";
    const update = () => {
      const p = Math.min(1, Math.max(0, (window.scrollY - top) / travel));
      const q = Math.min(1, Math.max(0, (p - 0.04) / 0.62)); // hand lets go, view moves into the soil
      const r = Math.min(1, Math.max(0, (p - 0.7) / 0.26)); // drawn roots grow on from the photo's root tips
      const at = q * last;
      const i = Math.floor(at);
      const k = at - i;
      const ui = Math.round((PLATE.ui[i] * (1 - k) + PLATE.ui[Math.min(last, i + 1)] * k) * mediaHeight * 2) / 2;
      if (ui !== lastUi) {
        lastUi = ui;
        for (const el of uiLayers) el.style.transform = `translate3d(0, ${ui}px, 0)`;
      }
      const rr = Math.round(r * 1000) / 1000;
      if (rr !== lastR && rootsSvg) {
        lastR = rr;
        rootsSvg.style.setProperty("--r", String(rr));
      }
      const qq = Math.round(q * 1000) / 1000;
      if (qq !== lastQ && caption) {
        lastQ = qq;
        caption.style.setProperty("--q", String(qq));
      }
      const phase = q > 0.002 ? "plate" : "hero";
      if (phase !== lastPhase) {
        lastPhase = phase;
        section.dataset.phase = phase;
        if (phase === "plate") loop.pause();
        else if (loop.classList.contains("is-on") && !reduced) void loop.play()?.catch(() => undefined);
      }
      target = Math.min(at / PLATE.fps, Math.max(0, (plate.duration || 1) - 0.002));
      if (plate.readyState >= 1) seek();
    };
    const onResize = () => {
      measure();
      update();
    };
    measure();
    update();
    plate.addEventListener("loadedmetadata", update);
    // Native scroll, plus the smooth-scroll engine's own event so animation and scroll land in the same frame.
    window.addEventListener("scroll", update, { passive: true });
    window.addEventListener("landing:scroll", update);
    window.addEventListener("resize", onResize);
    return () => {
      plate.removeEventListener("seeked", onSeeked);
      plate.removeEventListener("loadedmetadata", update);
      window.removeEventListener("scroll", update);
      window.removeEventListener("landing:scroll", update);
      window.removeEventListener("resize", onResize);
    };
  }, []);

  // When the intro (roots growing) ends, hand over to the seamless loop (roots swaying).
  const startLoop = () => {
    const loop = loopRef.current;
    if (!loop) return;
    loop.currentTime = 0;
    const playing = loop.play();
    if (playing) playing.then(() => setLooping(true)).catch(() => undefined);
    else setLooping(true);
  };

  const t = m.landing.hero;
  return (
    <section ref={sectionRef} className="s-hero" data-phase="hero" aria-label={t.title.replace("\n", " ")}>
      <div className="hero-sticky">
        <div ref={mediaRef} className="hero-media" aria-hidden="true">
          <video ref={introRef} className="hero-video" src="/media/hero-intro.mp4" poster="/media/hero-poster.jpg" muted playsInline preload="auto" onEnded={startLoop} />
          <video ref={loopRef} className={`hero-video hero-loop${looping ? " is-on" : ""}`} src="/media/hero-loop.mp4" muted playsInline loop preload="auto" />
          <video ref={plateRef} className="hero-video hero-plate" src="/media/hero-plate.mp4" muted playsInline preload="auto" />
          <svg className="root-continue" viewBox={`0 0 ${PLATE.width} ${PLATE.height}`} preserveAspectRatio="none">
            {CONTINUATION.map((root, i) => (
              <path key={i} d={root.d} pathLength={1} className={`cont-root root cont-root--d${root.depth}`}
                style={{ strokeWidth: root.width, "--s": root.start.toFixed(3), "--l": root.span.toFixed(3) } as React.CSSProperties} />
            ))}
          </svg>
          <div className="hero-ui-media">
            <div className="ai ai-box" style={{ "--d": "1.3s" } as React.CSSProperties}>
              <i /><i /><i /><i /><span className="ai-ring" />
              <Image className="ai-sprout" src="/images/hero-sprout.png" alt="" width={110} height={152} priority />
            </div>
            <div className="ai ai-tag" style={{ "--d": "1.7s" } as React.CSSProperties}>{t.moisture}</div>
            <div className="ai ai-label" style={{ "--d": "1.9s" } as React.CSSProperties}>{t.leafHealth} <b>92%</b></div>
            <div className="ai ai-small" style={{ "--d": "2.2s" } as React.CSSProperties}><i /><i /><i /><i /></div>
          </div>
        </div>
        <div className="hero-ui">
          <div className="hero-copy">
            <h1><Lines text={t.title} /></h1>
            <DemoButton className="demo-btn--glass" />
          </div>
          <div className="hero-caption">
            <p>{t.caption}</p>
            <ScrollHint />
          </div>
        </div>
      </div>
    </section>
  );
}

/* ---------- 1. Roots: the soil below the seedling (the video at 00:03) ---------- */

const BENEFIT_ICONS = [
  "M4 4l16 16M9 9a4 4 0 0 0 6 6M12 4a8 8 0 0 1 8 8",
  "M4 7h16v12H4zM8 7V5h8v2M9 13h6",
  "M12 4a8 8 0 1 0 8 8M12 8a4 4 0 1 0 4 4M12 12l6-6",
  "M12 3l7 3v6c0 4-3 7-7 9-4-2-7-5-7-9V6z",
];

function RootOpening() {
  const { m } = useI18n();
  const t = m.landing.about;
  return (
    <section className="s-roots" aria-label={t.mark}>
      <div className="roots-soil" aria-hidden="true" />

      <div className="roots-about">
        <div data-reveal="up">
          <Mark>{t.mark}</Mark>
          <h2><Lines text={t.title} /></h2>
        </div>
        <p data-reveal="up">{t.text}</p>
      </div>

      <div className="microbe" data-reveal="iris">
        <div className="microbe-bar"><span>{t.moistureCard}</span><b data-count="64">0%</b></div>
        <div className="microbe-img"><Photo src="/images/ref-soil-microbiology.jpg" alt="Close-up of moist soil around fine roots" sizes="(max-width: 720px) 80vw, 420px" /></div>
        <svg className="microbe-arc" viewBox="0 0 400 60" aria-hidden="true">
          <path d="M10 6 Q200 70 390 6" />
          <circle className="microbe-dot" r="5" />
          <circle cx="200" cy="38" r="2.5" fill="#fff" />
        </svg>
      </div>

      <div className="benefits">
        <p>{t.delivers}</p>
        <div className="benefit-grid">
          {BENEFIT_ICONS.map((icon, i) => (
            <article key={icon} data-reveal="up" style={{ "--i": i } as React.CSSProperties}>
              <span className="benefit-icon"><svg viewBox="0 0 24 24" aria-hidden="true"><path d={icon} /></svg></span>
              <div><strong>{t.benefits[i].title}</strong><small>{t.benefits[i].sub}</small></div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ---------- 2. Problem: three scroll states over one crop row ---------- */

function ProblemScene() {
  const { m } = useI18n();
  const t = m.landing.problem;
  return (
    <section className="s-problem scrub" data-scrub data-steps={t.steps.length} aria-label={t.title.replace("\n", " ")}>
      <div className="sticky">
        <div className="grid-bg" aria-hidden="true" />
        <header className="center-head">
          <Mark>{t.mark}</Mark>
          <h2><Lines text={t.title} /></h2>
        </header>

        <div className="problem-axis" aria-hidden="true">
          <i className="axis-ticks" />
          {t.steps.map((step, i) => <span key={i} className={`axis-label axis-label--${i}`}>{step.label}</span>)}
        </div>

        <svg className="crop-row" viewBox="0 0 900 320" role="img" aria-label={t.steps.map((step) => step.label).join(" · ")}>
          <g transform="translate(0 -64)">
          <g className="sprayer">
            <path d="M120 120h24v18h-24zM144 128h18l8 10h-26M124 140a6 6 0 1 0 0.1 0M158 140a6 6 0 1 0 0.1 0" />
            <path d="M170 126h290" />
            {[220, 290, 360, 430].map((x) => (
              <g key={x}>
                <path className="spray-arc" d={`M${x - 30} 126 Q${x} 70 ${x + 30} 126`} />
                <path className="spray-cone" d={`M${x} 126 l-14 40 M${x} 126 l0 42 M${x} 126 l14 40`} />
              </g>
            ))}
          </g>
          </g>
          <g className="tank"><path d="M150 186h28v44h-28zM158 178h12v8M146 230h36" /></g>
          <path className="soil" d="M120 230h680" />
          {CROPS.map((plant, i) => (
            <g key={i} className="crop" style={{ "--i": i } as React.CSSProperties}>
              <path className="crop-roots" d={plant.roots} />
              <path className="crop-stem" d={plant.stem} />
              <path className="crop-leaves" d={plant.leaves} />
            </g>
          ))}
          <g className="pests">
            {[[606, 120], [650, 150], [700, 112], [740, 160], [620, 176]].map(([x, y], i) => (
              <g key={i} style={{ "--i": i } as React.CSSProperties}>
                <circle cx={x} cy={y} r="11" />
                <circle cx={x} cy={y} r="3.5" className="pest-core" />
              </g>
            ))}
            <path className="pest-trail" d="M606 120 C640 96 690 96 700 112 S740 140 740 160" />
          </g>
          <path className="strain-band" d="M200 80 L780 152 L780 182 L200 112 Z" />
        </svg>

        <DemoButton />
        <div className="problem-notes">
          {t.steps.map((step, i) => <p key={i} className={`problem-note problem-note--${i}`}>{step.note}</p>)}
        </div>
      </div>
    </section>
  );
}

/* ---------- 3. Vision → Action ---------- */

function VisionAction() {
  const { m, dir } = useI18n();
  const t = m.landing.bridge;
  // Read right-to-left in Arabic: the first word sits on the right.
  const [first, second] = dir === "rtl" ? [t.action, t.vision] : [t.vision, t.action];
  return (
    <section className="s-bridge scrub" data-scrub aria-label={`${t.vision} · ${t.action}`}>
      <div className="sticky">
        <div className="bridge-lines" aria-hidden="true">
          {Array.from({ length: 14 }, (_, i) => <i key={i} style={{ "--i": i } as React.CSSProperties} />)}
        </div>
        <div className="bridge-words">
          <strong className="w-vision">{first}</strong>
          <div className="bridge-diamond" aria-hidden="true"><span>{t.diamond}</span></div>
          <strong className="w-action">{second}</strong>
        </div>
        <p className="bridge-copy">{t.copy}</p>
      </div>
    </section>
  );
}

/* ---------- 4. Live field map ---------- */

function FieldMap() {
  const { m } = useI18n();
  const t = m.landing.map;
  return (
    <section className="s-map scrub" data-scrub aria-label={t.zones.join(" · ")}>
      <div className="sticky">
        <div className="map-photo"><Photo src="/images/farmlink-field-aerial.jpg" alt="Aerial view of farm fields mapped by soil moisture" /></div>
        <div className="map-tint" aria-hidden="true" />
        {t.zones.map((label, i) => (
          <div key={i} className={`zone-tag z${i + 1}`}><i aria-hidden="true" /><span>{label}</span></div>
        ))}
        <div className="map-scale">
          <div className="map-scale-labels">{t.scale.map((label) => <span key={label}>{label}</span>)}</div>
          <div className="map-scale-bar"><i /></div>
          <div className="map-scale-months">{t.months.map((label) => <span key={label}>{label}</span>)}</div>
        </div>
      </div>
    </section>
  );
}

/* ---------- 5. How it works ---------- */

const PROCESS_IMAGES = ["/images/farmlink-field-aerial.jpg", "/images/ref-field-scouts.jpg", "/images/ref-field-sprayer.jpg"];

function HowItWorks() {
  const { m } = useI18n();
  const t = m.landing.process;
  const steps = t.steps.map((step, i) => ({ ...step, image: PROCESS_IMAGES[i] }));
  return (
    <section className="s-process scrub" data-scrub data-steps={steps.length} aria-label={t.label}>
      <div className="sticky">
        <div className="process-left">
          {steps.map((p, i) => (
            <div key={i} className={`process-photo process-photo--${i}`}><Photo src={p.image} alt={p.title} sizes="(max-width: 720px) 100vw, 50vw" /></div>
          ))}
          <div className="process-ring" aria-hidden="true">
            <span className="ring-count">[<b className="rc rc--0">01</b><b className="rc rc--1">02</b><b className="rc rc--2">03</b> / 03]</span>
            <span className="ring-label">{t.label}</span>
          </div>
        </div>
        <div className="process-right">
          <div className="process-blur" aria-hidden="true"><Photo src="/images/farmlink-crop-health.jpg" alt="" sizes="50vw" /></div>
          <ol className="process-list">
            {steps.map((p, i) => (
              <li key={i} className={`process-item process-item--${i}`}>
                <h3><span>0{i + 1}</span>{p.title}</h3>
                <div className="process-body">
                  <p>{p.text}</p>
                  <div className="process-thumb"><Photo src={p.image} alt="" sizes="300px" /></div>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </section>
  );
}

/* ---------- 6. Platform ---------- */

function Platform() {
  const { m } = useI18n();
  const t = m.landing.platform;
  return (
    <section className="s-platform" aria-label={t.title.replace("\n", " ")}>
      <div className="platform-bg"><Photo src="/images/farmlink-crop-health.jpg" alt="" /></div>
      <div className="platform-head">
        <div data-reveal="up"><Mark>{t.mark}</Mark><h2><Lines text={t.title} /></h2></div>
        <div data-reveal="up"><p>{t.text}</p><DemoButton /></div>
      </div>
      <div className="platform-cards">
        <article data-reveal="up">
          <Brackets />
          <span className="card-index">[01]</span>
          <div className="card-visual">
            <Photo src="/images/ref-seedling-outcomes.jpg" alt={t.cards[0].title} sizes="(max-width: 720px) 90vw, 30vw" />
            <span className="detect detect--a">{t.cards[0].tagA}</span>
            <span className="detect detect--b">{t.cards[0].tagB}</span>
          </div>
          <h3>{t.cards[0].title}</h3>
          <p>{t.cards[0].text}</p>
        </article>
        <article data-reveal="up" style={{ "--i": 1 } as React.CSSProperties}>
          <Brackets />
          <span className="card-index">[02]</span>
          <div className="card-visual dash">
            <div className="dash-side"><i /><i /><i /><i /></div>
            <div className="dash-main">
              <span className="dash-hello">{t.cards[1].hello}</span>
              <div className="dash-map"><i /></div>
              <div className="dash-stats"><b>64%</b><b>24°C</b><b>1.2k L</b></div>
              <div className="dash-rows"><i /><i /><i /></div>
            </div>
          </div>
          <h3>{t.cards[1].title}</h3>
          <p>{t.cards[1].text}</p>
        </article>
        <article data-reveal="up" style={{ "--i": 2 } as React.CSSProperties}>
          <Brackets />
          <span className="card-index">[03]</span>
          <div className="card-visual">
            <Photo src="/images/farmlink-rootloop-water.jpg" alt={t.cards[2].title} sizes="(max-width: 720px) 90vw, 30vw" />
            <span className="detect detect--c">{t.cards[2].tagA}</span>
            <span className="detect detect--d">{t.cards[2].tagB}</span>
          </div>
          <h3>{t.cards[2].title}</h3>
          <p>{t.cards[2].text}</p>
        </article>
      </div>
    </section>
  );
}

/* ---------- 7. Outcomes ---------- */

const OUTCOME_IMAGES = ["/images/ref-field-sprayer.jpg", "/images/farmlink-field-aerial.jpg", "/images/ref-seedling-outcomes.jpg", "/images/farmlink-crop-health.jpg"];

function Outcomes() {
  const { m } = useI18n();
  const t = m.landing.outcomes;
  const items = t.items.map((item, i) => ({ ...item, image: OUTCOME_IMAGES[i] }));
  return (
    <section className="s-outcomes scrub" data-scrub data-steps={items.length} aria-label={t.title.replace("\n", " ")}>
      <div className="sticky">
        <header className="center-head">
          <Mark>{t.mark}</Mark>
          <h2><Lines text={t.title} /></h2>
        </header>
        <div className="outcome-copy">
          {items.map((o, i) => (
            <div key={i} className={`outcome-text outcome-text--${i}`}>
              <h3>{o.title}</h3>
              <p>{o.text}</p>
              <DemoButton />
            </div>
          ))}
        </div>
        <div className="outcome-visual">
          {items.map((o, i) => (
            <div key={i} className={`outcome-photo outcome-photo--${i}`}><Photo src={o.image} alt={o.title} sizes="(max-width: 720px) 90vw, 45vw" /></div>
          ))}
          <span className="outcome-logo" aria-hidden="true"><BrandLogo size={34} className="rounded-lg" /></span>
          <div className="metric">
            <Brackets />
            {items.map((o, i) => <strong key={i} className={`metric-v metric-v--${i}`}>{o.value}<small>{o.unit}</small></strong>)}
            <svg viewBox="0 0 120 40" aria-hidden="true"><path d="M2 34 C30 32 50 30 70 22 S100 8 118 4" /></svg>
            <div className="metric-months">{t.months.map((label) => <span key={label}>{label}</span>)}</div>
          </div>
          <i className="corner-lime" aria-hidden="true" />
        </div>
      </div>
    </section>
  );
}

/* ---------- 8. Use cases ---------- */

const CROP_IMAGES = [
  "/images/farmlink-field-aerial.jpg",
  "/images/farmlink-crop-health.jpg",
  "/images/ref-vineyard-gallery.jpg",
  "/images/farmlink-rootloop-water.jpg",
  "/images/ref-seedling-outcomes.jpg",
  "/images/ref-soil-microbiology.jpg",
  "/images/ref-field-scouts.jpg",
];

function UseCases() {
  const { m } = useI18n();
  const t = m.landing.useCases;
  const crops = t.crops.map((crop, i) => ({ ...crop, src: CROP_IMAGES[i] }));
  const [active, setActive] = useState(2);
  return (
    <section className="s-usecases" aria-label={t.title.replace("\n", " ")}>
      <header className="use-head" data-reveal="up">
        <Mark>{t.mark}</Mark>
        <h2><Lines text={t.title} /></h2>
      </header>
      <div className="use-track" style={{ "--active": active } as React.CSSProperties}>
        {crops.map((c, i) => (
          <button key={i} type="button" className={`use-card${i === active ? " is-active" : ""}`} onClick={() => setActive(i)} aria-pressed={i === active} aria-label={c.label}>
            <Photo src={c.src} alt="" sizes={i === active ? "(max-width: 720px) 70vw, 340px" : "160px"} />
            {i === active && <span className="use-chip"><BrandMark />{c.label}</span>}
            {i === active && <span className="use-text">{c.text}</span>}
          </button>
        ))}
      </div>
      <div className="use-ruler">
        {crops.map((c, i) => (
          <button key={i} type="button" className={i === active ? "is-active" : ""} onClick={() => setActive(i)}>{c.label}</button>
        ))}
        <i style={{ "--active": active } as React.CSSProperties} aria-hidden="true" />
      </div>
    </section>
  );
}

/* ---------- 9. The market shift (floating field block) ---------- */

function MarketShift() {
  const { m } = useI18n();
  const t = m.landing.shift;
  return (
    <section className="s-shift" aria-label={t.title.replace("\n", " ")}>
      <div className="mist mist--a" aria-hidden="true" />
      <div className="mist mist--b" aria-hidden="true" />
      <header className="shift-head" data-reveal="up">
        <Mark>{t.mark}</Mark>
        <h2><Lines text={t.title} /></h2>
      </header>
      <div className="block-wrap" aria-hidden="true">
        <div className="terrain-block">
          <div className="block-top">
            <Photo src="/images/farmlink-field-aerial.jpg" alt="" sizes="600px" />
            <i className="plot plot--a" /><i className="plot plot--b" /><i className="plot plot--c" /><i className="plot plot--d" />
          </div>
          <div className="block-side block-side--front" />
          <div className="block-side block-side--right" />
        </div>
      </div>
      <div className="glass glass--risk" data-reveal="left">
        <div className="glass-title"><strong>{t.statusTitle}</strong><span aria-hidden="true">⌘</span></div>
        <div className="risk">
          <span className="risk-axis"><b>{t.max}</b><b>{t.min}</b></span>
          {[["38–46%", t.bars[0], "lime", 0.7], ["20–35%", t.bars[1], "straw", 0.55], ["5–8%", t.bars[2], "orange", 0.35]].map(([range, label, tone, h]) => (
            <div key={label as string} className="risk-col">
              <small>{range}</small>
              <span className="risk-track"><i className={`risk-fill risk-fill--${tone}`} style={{ "--h": h } as React.CSSProperties} /></span>
              <small>{label}</small>
            </div>
          ))}
        </div>
      </div>
      <div className="glass glass--chem" data-reveal="right">
        <div className="glass-title"><strong>{t.useTitle}</strong><span aria-hidden="true">⌘</span></div>
        <small className="glass-sub"><IconTrendDown /> {t.useSub}</small>
        <svg viewBox="0 0 200 70" aria-hidden="true">
          <path className="chem-line" d="M4 60 L40 56 L76 50 L112 40 L148 30 L196 10" />
          <circle cx="196" cy="10" r="3" />
        </svg>
        <span className="chem-call">−12%</span>
        <div className="metric-months">{t.months.map((label) => <span key={label}>{label}</span>)}</div>
      </div>
      <ScrollHint />
    </section>
  );
}

/* ---------- 10. Start with precision + 11. Grow with less ---------- */

const LEAF_TONES = ["#3f6a24", "#4d7a2c", "#5e8c34", "#2f5420", "#6f9a3e"];
const FLOWER_TONES = ["#fbf6ee", "#f6e9ef", "#fff8e6"];

function Shrub() {
  return (
    <svg className="shrub" viewBox="0 0 500 280" aria-hidden="true">
      <ellipse cx="250" cy="292" rx="260" ry="40" fill="#7c9a3c" />
      {SHRUB.map((p, i) => {
        const t = `translate(${p.x.toFixed(1)} ${p.y.toFixed(1)}) rotate(${p.rot.toFixed(0)})`;
        if (p.kind === "stem") return <path key={i} d={`M0 0 l0 ${(-p.r).toFixed(0)}`} transform={t} stroke="#3c5a22" strokeWidth="1.4" />;
        if (p.kind === "leaf") return <ellipse key={i} rx={p.r.toFixed(1)} ry={(p.r * 0.42).toFixed(1)} transform={t} fill={LEAF_TONES[p.tone]} />;
        return (
          <g key={i} transform={t}>
            {[0, 72, 144, 216, 288].map((a) => <ellipse key={a} cx="0" cy={(-p.r * 0.55).toFixed(1)} rx={(p.r * 0.42).toFixed(1)} ry={(p.r * 0.6).toFixed(1)} transform={`rotate(${a})`} fill={FLOWER_TONES[p.tone]} />)}
            <circle r={(p.r * 0.3).toFixed(1)} fill="#e3b94a" />
          </g>
        );
      })}
    </svg>
  );
}

function Join() {
  const { m } = useI18n();
  const t = m.landing.join;
  return (
    <section className="s-join" id="join" aria-label={t.title.replace("\n", " ")}>
      <div className="join-copy" data-reveal="up">
        <h2><Lines text={t.title} /></h2>
        <p>{t.text}</p>
        <DemoButton href="/login">{m.common.bookDemo}</DemoButton>
      </div>
      <div className="join-plant">
        <Shrub />
        <div className="bees" aria-hidden="true">{Array.from({ length: 6 }, (_, i) => <i key={i} style={{ "--i": i } as React.CSSProperties} />)}</div>
      </div>
    </section>
  );
}

function Closing() {
  const { m } = useI18n();
  const t = m.landing.closing;
  const icons = ["M4 8a4 4 0 0 1 4-4h8a4 4 0 0 1 4 4v8a4 4 0 0 1-4 4H8a4 4 0 0 1-4-4zM12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6", "M5 4h14v16H5zM9 9h6M9 13h6", "M4 12l16-7-5 15-3-6z", "M5 5l14 14M19 5L5 19"];
  return (
    <section className="s-closing" aria-label={t.title}>
      <div className="closing-diamond" data-reveal="iris"><div><Shrub /></div><i /><i /><i /><i /></div>
      <h2 data-reveal="up">{t.title}</h2>
      <p data-reveal="up">{t.text}</p>
      <div className="closing-icons" data-reveal="up">
        {icons.map((d, i) => <a key={i} href="#join" aria-label={["Instagram", "Blog", "Telegram", "X"][i]}><svg viewBox="0 0 24 24" aria-hidden="true"><path d={d} /></svg></a>)}
      </div>
      <footer className="closing-foot"><span>{t.rights}</span><i aria-hidden="true" /><span>{t.tagline}</span></footer>
    </section>
  );
}

/* ---------- page ---------- */

export default function LandingPage() {
  const rootRef = useRef<HTMLElement>(null);

  useEffect(() => {
    const page = rootRef.current;
    if (!page) return;
    const reduced =
      typeof window.matchMedia !== "function" ||
      !("IntersectionObserver" in window) ||
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!reduced) document.documentElement.classList.add("motion-ok");

    // Reveal on enter (and count-ups such as "Microbial activity").
    const reveal = page.querySelectorAll<HTMLElement>("[data-reveal]");
    const counters = new WeakSet<Element>();
    const runCount = (el: HTMLElement) => {
      if (counters.has(el)) return;
      counters.add(el);
      const target = Number(el.dataset.count);
      const start = performance.now();
      const tick = (now: number) => {
        const t = Math.min(1, (now - start) / 1600);
        el.textContent = `${Math.round(target * (1 - Math.pow(1 - t, 3)))}%`;
        if (t < 1) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    };
    const observer = reduced
      ? undefined
      : new IntersectionObserver(
          (entries) => entries.forEach((e) => {
            if (!e.isIntersecting) return;
            e.target.classList.add("in");
            e.target.querySelectorAll<HTMLElement>("[data-count]").forEach(runCount);
          }),
          { threshold: 0.2 },
        );
    reveal.forEach((el) => (observer ? observer.observe(el) : el.classList.add("in")));
    if (reduced) page.querySelectorAll<HTMLElement>("[data-count]").forEach((el) => (el.textContent = `${el.dataset.count}%`));

    // Scroll-scrubbed sections: --p goes 0→1 while the sticky panel is pinned; data-step picks the state.
    // Positions are measured once (and whenever the page resizes), so scrolling never forces a layout.
    type Scrub = { el: HTMLElement; top: number; height: number; steps: number; lastP: number; lastStep: number };
    const scrubEls = Array.from(page.querySelectorAll<HTMLElement>("[data-scrub]"));
    const signIn = document.querySelector<HTMLElement>(".site-nav-signin");
    const lightEls = Array.from(page.querySelectorAll<HTMLElement>(".s-problem, .s-bridge, .s-outcomes, .s-usecases, .s-join"));
    let scrubs: Scrub[] = [];
    let lightRanges: Array<[number, number]> = [];
    const measure = () => {
      const y = window.scrollY;
      scrubs = scrubEls.map((el) => {
        const r = el.getBoundingClientRect();
        return { el, top: r.top + y, height: r.height, steps: Number(el.dataset.steps || 0), lastP: -1, lastStep: -1 };
      });
      lightRanges = lightEls.map((el) => {
        const r = el.getBoundingClientRect();
        return [r.top + y, r.bottom + y];
      });
    };
    let onLight: boolean | null = null;
    const update = () => {
      const y = window.scrollY;
      const vh = window.innerHeight;
      if (signIn) {
        const probe = y + 36; // the Sign In link's line
        const light = lightRanges.some(([a, b]) => probe >= a && probe < b);
        if (light !== onLight) {
          onLight = light;
          signIn.classList.toggle("on-light", light);
        }
      }
      for (const s of scrubs) {
        if (y + vh * 2 < s.top || y > s.top + s.height + vh) continue;
        const p = Math.min(1, Math.max(0, (y - s.top) / Math.max(1, s.height - vh)));
        const rounded = Math.round(p * 2000) / 2000;
        if (rounded !== s.lastP) {
          s.lastP = rounded;
          s.el.style.setProperty("--p", String(rounded));
        }
        if (s.steps) {
          const step = Math.min(s.steps - 1, Math.floor(p * s.steps));
          if (step !== s.lastStep) {
            s.lastStep = step;
            s.el.dataset.step = String(step);
          }
        }
      }
    };
    const onResize = () => {
      measure();
      update();
    };
    measure();
    update();
    const resizeObserver = typeof ResizeObserver === "function" ? new ResizeObserver(onResize) : undefined;
    resizeObserver?.observe(page);
    window.addEventListener("scroll", update, { passive: true });
    window.addEventListener("landing:scroll", update);
    window.addEventListener("resize", onResize);

    // Smooth, eased wheel scrolling (touch keeps the phone's native scrolling). Its scroll callback runs in the
    // same frame as the scroll position change, so every scroll-driven animation stays in lock-step with it.
    let lenis: Lenis | undefined;
    let rafId = 0;
    if (!reduced) {
      lenis = new Lenis({ lerp: 0.09, wheelMultiplier: 0.9, smoothWheel: true, anchors: true });
      lenis.on("scroll", () => window.dispatchEvent(new Event("landing:scroll")));
      const raf = (time: number) => {
        lenis?.raf(time);
        rafId = requestAnimationFrame(raf);
      };
      rafId = requestAnimationFrame(raf);
    }

    return () => {
      observer?.disconnect();
      resizeObserver?.disconnect();
      window.removeEventListener("scroll", update);
      window.removeEventListener("landing:scroll", update);
      window.removeEventListener("resize", onResize);
      cancelAnimationFrame(rafId);
      lenis?.destroy();
      document.documentElement.classList.remove("motion-ok");
    };
  }, []);

  return (
    <main ref={rootRef} className="landing">
      <LandingNav />
      <InstallBanner />
      <Hero />
      <RootOpening />
      <ProblemScene />
      <VisionAction />
      <FieldMap />
      <HowItWorks />
      <Platform />
      <Outcomes />
      <UseCases />
      <MarketShift />
      <Join />
      <Closing />
    </main>
  );
}
