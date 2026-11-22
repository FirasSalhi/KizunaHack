import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import HomePage from "@/app/page";

describe("HomePage", () => {
  it("opens on the hero with the seedling roots", () => {
    render(<HomePage />);
    expect(screen.getByRole("heading", { level: 1, name: /Grow more/ })).toBeInTheDocument();
    // Drawn roots that continue from the photo root tips.
    expect(document.querySelectorAll(".cont-root").length).toBeGreaterThan(20);
  });
});
