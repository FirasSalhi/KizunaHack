"use client";

import React, { useEffect, useId, useRef, useState } from "react";
import { LOCALES, LOCALE_LABELS, type Locale } from "./config";
import { useI18n } from "./I18nProvider";

/**
 * Language dropdown: a button showing the current language that opens a list of all languages.
 * Keyboard: Enter/Space/ArrowDown opens it; arrows move; Enter/Space picks; Escape or Tab closes.
 * `tone` adapts it to dark or light surroundings.
 */
export function LanguageSwitcher({
  className = "",
  tone = "dark",
  placement = "down",
  align = "end",
}: {
  className?: string;
  tone?: "dark" | "light";
  /** "up" opens the list above the button (e.g. near the bottom of a sidebar). */
  placement?: "down" | "up";
  align?: "end" | "start";
}) {
  const { locale, setLocale, m } = useI18n();
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(LOCALES.indexOf(locale));
  const rootRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const optionRefs = useRef<Array<HTMLLIElement | null>>([]);
  const listId = useId();

  // Close when clicking or tapping anywhere outside.
  useEffect(() => {
    if (!open) return;
    const onPointer = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", onPointer);
    return () => document.removeEventListener("pointerdown", onPointer);
  }, [open]);

  // Keep keyboard focus on the highlighted option while the list is open.
  useEffect(() => {
    if (open) optionRefs.current[active]?.focus();
  }, [open, active]);

  const openList = () => {
    setActive(LOCALES.indexOf(locale));
    setOpen(true);
  };
  const choose = (code: Locale) => {
    setLocale(code);
    setOpen(false);
    buttonRef.current?.focus();
  };

  const onButtonKey = (event: React.KeyboardEvent) => {
    if (["ArrowDown", "ArrowUp", "Enter", " "].includes(event.key)) {
      event.preventDefault();
      openList();
    }
  };
  const onListKey = (event: React.KeyboardEvent) => {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActive((i) => (i + 1) % LOCALES.length);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActive((i) => (i - 1 + LOCALES.length) % LOCALES.length);
    } else if (event.key === "Home") {
      event.preventDefault();
      setActive(0);
    } else if (event.key === "End") {
      event.preventDefault();
      setActive(LOCALES.length - 1);
    } else if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      choose(LOCALES[active]);
    } else if (event.key === "Escape") {
      event.preventDefault();
      setOpen(false);
      buttonRef.current?.focus();
    } else if (event.key === "Tab") {
      setOpen(false);
    }
  };

  return (
    <div ref={rootRef} className={`lang-select lang-select--${tone} lang-select--${placement} lang-select--${align} ${open ? "is-open" : ""} ${className}`.trim()}>
      <button
        ref={buttonRef}
        type="button"
        className="lang-select-button"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={listId}
        aria-label={`${m.common.language}: ${LOCALE_LABELS[locale].name}`}
        onClick={() => (open ? setOpen(false) : openList())}
        onKeyDown={onButtonKey}
      >
        <svg className="lang-select-globe" viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="12" cy="12" r="9" />
          <path d="M3 12h18M12 3c2.6 2.5 4 5.6 4 9s-1.4 6.5-4 9c-2.6-2.5-4-5.6-4-9s1.4-6.5 4-9Z" />
        </svg>
        <span lang={locale}>{LOCALE_LABELS[locale].name}</span>
        <svg className="lang-select-chevron" viewBox="0 0 12 12" aria-hidden="true">
          <path d="M3 4.5 6 7.5 9 4.5" />
        </svg>
      </button>
      {open && (
        <ul id={listId} role="listbox" aria-label={m.common.language} className="lang-select-list">
          {LOCALES.map((code, i) => (
            <li
              key={code}
              ref={(el) => {
                optionRefs.current[i] = el;
              }}
              role="option"
              tabIndex={i === active ? 0 : -1}
              aria-selected={code === locale}
              lang={code}
              className={`lang-select-option${i === active ? " is-active" : ""}`}
              onClick={() => choose(code)}
              onKeyDown={onListKey}
              onMouseEnter={() => setActive(i)}
            >
              <span className="lang-select-code">{LOCALE_LABELS[code].short}</span>
              <span>{LOCALE_LABELS[code].name}</span>
              {code === locale && (
                <svg className="lang-select-check" viewBox="0 0 12 12" aria-hidden="true">
                  <path d="M2.5 6.5 5 9l4.5-6" />
                </svg>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
