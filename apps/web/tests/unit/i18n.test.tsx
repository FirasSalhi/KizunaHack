import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import LandingPage from "@/components/landing/LandingPage";
import { I18nProvider } from "@/i18n/I18nProvider";
import { LanguageSwitcher } from "@/i18n/LanguageSwitcher";
import ar from "@/i18n/messages/ar";
import en from "@/i18n/messages/en";
import fr from "@/i18n/messages/fr";
import ja from "@/i18n/messages/ja";

/** Every key path, with list lengths, so a catalog that drops an item is caught too. */
function shape(value: unknown, path = ""): string[] {
  if (Array.isArray(value)) return [`${path}[${value.length}]`, ...value.flatMap((v, i) => shape(v, `${path}[${i}]`))];
  if (value && typeof value === "object") return Object.entries(value).flatMap(([k, v]) => shape(v, path ? `${path}.${k}` : k));
  return [path];
}

describe("Languages", () => {
  it("French, Tunisian Arabic and Japanese have exactly the same keys and list lengths as English", () => {
    expect(shape(fr)).toEqual(shape(en));
    expect(shape(ar)).toEqual(shape(en));
    expect(shape(ja)).toEqual(shape(en));
  });

  it("renders the landing page in Japanese", () => {
    render(
      <I18nProvider initialLocale="ja">
        <LandingPage />
      </I18nProvider>,
    );
    expect(screen.getByRole("heading", { level: 1, name: /もっと育てる/ })).toBeInTheDocument();
  });

  it("renders the landing page in French", () => {
    render(
      <I18nProvider initialLocale="fr">
        <LandingPage />
      </I18nProvider>,
    );
    expect(screen.getByRole("heading", { level: 1, name: /Cultivez plus/ })).toBeInTheDocument();
  });

  it("renders the landing page in Tunisian Arabic", () => {
    render(
      <I18nProvider initialLocale="ar">
        <LandingPage />
      </I18nProvider>,
    );
    expect(screen.getByRole("heading", { level: 1, name: /زيد في الصابة/ })).toBeInTheDocument();
  });

  it("switches language and page direction from the dropdown", () => {
    render(
      <I18nProvider initialLocale="fr">
        <LanguageSwitcher />
      </I18nProvider>,
    );
    const button = screen.getByRole("button", { name: /Langue/ });
    expect(button).toHaveAttribute("aria-expanded", "false");

    fireEvent.click(button);
    expect(screen.getAllByRole("option")).toHaveLength(4);
    fireEvent.click(screen.getByRole("option", { name: /الدارجة/ }));
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    expect(document.documentElement.dir).toBe("rtl");
    expect(document.documentElement.lang).toBe("ar");
    expect(document.cookie).toContain("fl_locale=ar");

    fireEvent.click(screen.getByRole("button", { name: /اللغة/ }));
    fireEvent.click(screen.getByRole("option", { name: /日本語/ }));
    expect(document.documentElement.lang).toBe("ja");
    expect(document.documentElement.dir).toBe("ltr");
  });

  it("can be used with the keyboard", () => {
    render(
      <I18nProvider initialLocale="fr">
        <LanguageSwitcher />
      </I18nProvider>,
    );
    fireEvent.keyDown(screen.getByRole("button", { name: /Langue/ }), { key: "ArrowDown" });
    fireEvent.keyDown(screen.getByRole("option", { name: /Français/ }), { key: "End" }); // jump to the last option: Japanese
    fireEvent.keyDown(screen.getByRole("option", { name: /日本語/ }), { key: "Enter" });
    expect(document.documentElement.lang).toBe("ja");
    fireEvent.keyDown(screen.getByRole("button", { name: /言語/ }), { key: "Enter" });
    fireEvent.keyDown(screen.getByRole("option", { name: /日本語/ }), { key: "Escape" });
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });
});
