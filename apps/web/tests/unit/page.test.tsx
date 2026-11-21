import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import HomePage from "@/app/page";

describe("HomePage", () => {
  it("renders FARMLINK", () => {
    render(<HomePage />);
    expect(screen.getByText("FARMLINK")).toBeInTheDocument();
  });
});
