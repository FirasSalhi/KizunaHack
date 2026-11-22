import "@testing-library/jest-dom/vitest";

// Mock HTMLMediaElement play and pause for JSDOM
window.HTMLMediaElement.prototype.play = () => Promise.resolve();
window.HTMLMediaElement.prototype.pause = () => {};

