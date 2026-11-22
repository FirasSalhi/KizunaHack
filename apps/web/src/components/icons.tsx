// Small line icons drawn in SVG (no emoji). They size with the surrounding text (1em) and use its colour.
import type { SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement>;

function Icon({ children, ...props }: IconProps & { children: React.ReactNode }) {
  return (
    <svg
      viewBox="0 0 24 24"
      width="1em"
      height="1em"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      {...props}
    >
      {children}
    </svg>
  );
}

/** FARMLINK mark: an eight-spoke asterisk. */
export function BrandMark(props: IconProps) {
  return (
    <Icon strokeWidth={2.6} {...props}>
      <path d="M12 3v18M3 12h18M5.6 5.6l12.8 12.8M18.4 5.6 5.6 18.4" />
    </Icon>
  );
}

export function IconOverview(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M4 20V10M10 20V4M16 20v-7M22 20H2" />
    </Icon>
  );
}

export function IconDrop(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M12 3c3.5 4.2 6 7.6 6 10.6A6 6 0 0 1 6 13.6C6 10.6 8.5 7.2 12 3Z" />
    </Icon>
  );
}

export function IconLeaf(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M5 19c0-8 5-13 15-14-1 10-6 15-14 15" />
      <path d="M5 19c3-4 6-7 10-9" />
    </Icon>
  );
}

export function IconSignal(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M12 12v9M8.5 8.5a5 5 0 0 0 0 7M15.5 8.5a5 5 0 0 1 0 7M5.6 5.6a9 9 0 0 0 0 12.8M18.4 5.6a9 9 0 0 1 0 12.8" />
    </Icon>
  );
}

export function IconBolt(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M13 2 4 14h7l-1 8 9-12h-7l1-8Z" />
    </Icon>
  );
}

export function IconSignOut(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M14 4h4a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-4M9 16l-4-4 4-4M5 12h11" />
    </Icon>
  );
}

export function IconTrendDown(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M3 7l7 7 4-4 7 7M21 11v6h-6" />
    </Icon>
  );
}

/** A folded map with a pin: crop planning on the farm's map. */
export function IconPlanMap(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M9 4 3 6v14l6-2 6 2 6-2V4l-6 2-6-2Z" />
      <path d="M9 4v14M15 6v6" />
      <path d="M18 15.5c0 1.8-2 3.5-2 3.5s-2-1.7-2-3.5a2 2 0 1 1 4 0Z" />
    </Icon>
  );
}

/** A crate with a snowflake mark: harvest kept in cold storage. */
export function IconCrate(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M3 8h18v12H3zM5 8l2-4h10l2 4" />
      <path d="M12 11v6M9.4 12.5l5.2 3M14.6 12.5l-5.2 3" />
    </Icon>
  );
}

/** Fields seen in perspective with a water drop: the 3D irrigation farm. */
export function IconFields3D(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M2 20 6 11h12l4 9H2Z" />
      <path d="M12 11v9M4 15.5h16" />
      <path d="M12 2.5c1.6 1.9 2.5 3.2 2.5 4.3a2.5 2.5 0 0 1-5 0c0-1.1.9-2.4 2.5-4.3Z" />
    </Icon>
  );
}
