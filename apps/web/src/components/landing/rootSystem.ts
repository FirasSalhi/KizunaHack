// Deterministic generators for the root system (opening scene) and the line-art crop row
// (problem scene). A seeded random keeps server and client output identical, so hydration
// matches.

export type RootPath = { d: string; width: number; delay: number; duration: number; depth: number };

function seeded(seed: number) {
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const f = (n: number) => n.toFixed(1);

/**
 * A taproot with lateral roots and root hairs, growing down from (x, y).
 * Coordinates are in a 400 × 640 viewBox. `delay` is when each path starts drawing (s).
 */
export function buildRootSystem(seed = 7): RootPath[] {
  const rand = seeded(seed);
  const paths: RootPath[] = [];

  const grow = (
    x: number,
    y: number,
    angle: number,
    length: number,
    width: number,
    depth: number,
    start: number,
  ) => {
    const segments = Math.max(3, Math.round(length / 14));
    const points: Array<[number, number]> = [[x, y]];
    let a = angle;
    let cx = x;
    let cy = y;
    const step = length / segments;
    // Primary roots stay close to their heading; laterals bend down under gravity.
    const pull = depth === 0 ? 0.05 : depth === 1 ? 0.1 : 0.04;
    const wobble = depth === 0 ? 0.2 : 0.5;
    for (let i = 0; i < segments; i++) {
      a += (rand() - 0.5) * wobble;
      a += (Math.PI / 2 - a) * pull;
      cx += Math.cos(a) * step;
      cy += Math.sin(a) * step;
      points.push([cx, cy]);
    }

    let d = `M${f(points[0][0])} ${f(points[0][1])}`;
    for (let i = 1; i < points.length; i++) {
      const [px, py] = points[i - 1];
      const [qx, qy] = points[i];
      d += ` Q${f(px)} ${f(py)} ${f((px + qx) / 2)} ${f((py + qy) / 2)}`;
    }
    const last = points[points.length - 1];
    d += ` T${f(last[0])} ${f(last[1])}`;

    const duration = depth === 0 ? 1.6 + length / 260 : 0.45 + length / 160;
    paths.push({ d, width, delay: start, duration, depth });

    if (depth >= 2) return;
    const childCount = depth === 0 ? 6 + Math.floor(rand() * 3) : 2 + Math.floor(rand() * 2);
    for (let c = 0; c < childCount; c++) {
      const t = 0.12 + (c / childCount) * 0.78 + rand() * 0.05;
      const index = Math.min(points.length - 1, Math.max(1, Math.round(t * segments)));
      const [bx, by] = points[index];
      const [px, py] = points[index - 1];
      const heading = Math.atan2(by - py, bx - px);
      const side = (c + depth) % 2 === 0 ? -1 : 1;
      const childAngle = heading + side * (0.55 + rand() * 0.5);
      const childLength = depth === 0 ? (34 + rand() * 60) * (1 - t * 0.45) : 8 + rand() * 16;
      grow(bx, by, childAngle, childLength, depth === 0 ? 0.75 : 0.45, depth + 1, start + duration * t);
    }
  };

  // A fan of primary roots from the crown, like a seedling pulled from soil.
  const primaries = [
    { angle: -0.55, length: 240, width: 1.6 },
    { angle: -0.16, length: 330, width: 2.1 },
    { angle: 0.04, length: 400, width: 2.4 },
    { angle: 0.22, length: 300, width: 2 },
    { angle: 0.6, length: 230, width: 1.6 },
  ];
  primaries.forEach((p, i) => grow(200, 112, Math.PI / 2 + p.angle, p.length, p.width, 0, 0.7 + i * 0.12));
  return paths;
}

export type CropPlant = { stem: string; leaves: string; roots: string; x: number; height: number };

/** Line-art maize plants for the problem scene, in a 900 × 320 viewBox (soil line at y = 230). */
export function buildCropRow(count = 9, seed = 21): CropPlant[] {
  const rand = seeded(seed);
  const plants: CropPlant[] = [];
  for (let i = 0; i < count; i++) {
    const x = 210 + i * 66;
    const height = 120 + rand() * 40;
    const top = 230 - height;
    const stem = `M${x} 230 C${f(x - 2)} ${f(230 - height * 0.4)} ${f(x + 2)} ${f(230 - height * 0.7)} ${x} ${f(top)}`;
    let leaves = "";
    const leafCount = 5 + Math.floor(rand() * 2);
    for (let l = 0; l < leafCount; l++) {
      const ly = 222 - (l + 0.6) * (height / (leafCount + 0.8));
      const side = l % 2 === 0 ? -1 : 1;
      const span = 24 + rand() * 14 - l * 2;
      const droop = 10 + rand() * 12;
      leaves += `M${x} ${f(ly)} C${f(x + side * span * 0.4)} ${f(ly - 16)} ${f(x + side * span)} ${f(ly - 8)} ${f(x + side * span * 1.15)} ${f(ly + droop)} `;
    }
    leaves += `M${x} ${f(top)} l-4 -14 m4 14 l5 -12`;
    let roots = "";
    for (let r = 0; r < 6; r++) {
      const side = r % 2 === 0 ? -1 : 1;
      const spread = 6 + r * 3.4 + rand() * 4;
      const depth = 26 + rand() * 26;
      roots += `M${x} 230 C${f(x + side * spread * 0.3)} ${f(238 + r)} ${f(x + side * spread)} ${f(244 + depth * 0.4)} ${f(x + side * spread * 1.25)} ${f(230 + depth)} `;
    }
    plants.push({ stem, leaves: leaves.trim(), roots: roots.trim(), x, height });
  }
  return plants;
}

export type ShrubPart = { kind: "leaf" | "flower" | "stem"; x: number; y: number; r: number; rot: number; tone: number };

/** A dome-shaped flowering shrub in a 500 × 280 viewBox (ground at y = 280). */
export function buildShrub(seed = 5): ShrubPart[] {
  const rand = seeded(seed);
  const parts: ShrubPart[] = [];
  for (let i = 0; i < 26; i++) {
    const x = 250 + (rand() - 0.5) * 300;
    parts.push({ kind: "stem", x, y: 280, r: 60 + rand() * 120, rot: (x - 250) * 0.18 + (rand() - 0.5) * 20, tone: 0 });
  }
  for (let i = 0; i < 420; i++) {
    // Sample inside a half-ellipse dome, denser toward the middle.
    const u = rand() * Math.PI;
    const v = Math.sqrt(rand());
    const x = 250 + Math.cos(u) * 210 * v;
    const y = 280 - Math.sin(u) * 190 * v - 6;
    parts.push({ kind: "leaf", x, y, r: 5 + rand() * 7, rot: rand() * 180, tone: Math.floor(rand() * 5) });
  }
  for (let i = 0; i < 90; i++) {
    const u = 0.15 + rand() * (Math.PI - 0.3);
    const v = 0.35 + rand() * 0.65;
    const x = 250 + Math.cos(u) * 200 * v;
    const y = 280 - Math.sin(u) * 182 * v - 6;
    parts.push({ kind: "flower", x, y, r: 3.2 + rand() * 3.2, rot: rand() * 72, tone: Math.floor(rand() * 3) });
  }
  return parts;
}

export type GrowPath = { d: string; width: number; depth: number; start: number; span: number };

/**
 * Roots that continue the photo's root system: each one starts exactly at a photo root tip
 * (coordinates in the plate's 2560 × 1568 pixel space) and keeps growing downward, with side roots.
 * `start`/`span` place each path inside the scroll-driven growth window (0 → 1).
 */
export function buildRootContinuation(tips: Array<[number, number]>, seed = 11): GrowPath[] {
  const rand = seeded(seed);
  const paths: GrowPath[] = [];
  const grow = (x: number, y: number, angle: number, length: number, width: number, depth: number, start: number, span: number) => {
    const segments = Math.max(4, Math.round(length / 22));
    const step = length / segments;
    const pts: Array<[number, number]> = [[x, y]];
    let a = angle;
    let cx = x;
    let cy = y;
    for (let i = 0; i < segments; i++) {
      a += (rand() - 0.5) * (depth === 0 ? 0.22 : 0.45);
      a += (Math.PI / 2 - a) * (depth === 0 ? 0.06 : 0.1);
      cx += Math.cos(a) * step;
      cy += Math.sin(a) * step;
      pts.push([cx, cy]);
    }
    let d = `M${f(pts[0][0])} ${f(pts[0][1])}`;
    for (let i = 1; i < pts.length; i++) {
      const [px, py] = pts[i - 1];
      const [qx, qy] = pts[i];
      d += ` Q${f(px)} ${f(py)} ${f((px + qx) / 2)} ${f((py + qy) / 2)}`;
    }
    d += ` T${f(pts[pts.length - 1][0])} ${f(pts[pts.length - 1][1])}`;
    paths.push({ d, width, depth, start, span });
    if (depth >= 2) return;
    const children = depth === 0 ? 5 + Math.floor(rand() * 3) : 2;
    for (let c = 0; c < children; c++) {
      const t = 0.12 + (c / children) * 0.8 + rand() * 0.05;
      const i = Math.min(pts.length - 1, Math.max(1, Math.round(t * segments)));
      const heading = Math.atan2(pts[i][1] - pts[i - 1][1], pts[i][0] - pts[i - 1][0]);
      const side = (c + depth) % 2 === 0 ? -1 : 1;
      const childLen = depth === 0 ? (60 + rand() * 110) * (1 - t * 0.4) : 14 + rand() * 26;
      grow(pts[i][0], pts[i][1], heading + side * (0.6 + rand() * 0.5), childLen, depth === 0 ? 1.6 : 1, depth + 1, start + span * t, span * 0.45);
    }
  };
  tips.forEach(([x, y], i) => {
    const length = 300 + rand() * 180 - i * 18;
    grow(x, y, Math.PI / 2 + (rand() - 0.5) * 0.3, length, 3.2 - i * 0.2, 0, i * 0.05, 0.62);
  });
  return paths;
}
