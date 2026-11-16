import { initials } from "../lib/format";
import { Icon } from "./Icons";

const GRADIENTS: Array<[string, string]> = [
  ["#6366f1", "#8b5cf6"],
  ["#06b6d4", "#3b82f6"],
  ["#10b981", "#14b8a6"],
  ["#f59e0b", "#f97316"],
  ["#ec4899", "#a855f7"],
  ["#ef4444", "#f97316"],
  ["#14b8a6", "#22d3ee"],
  ["#8b5cf6", "#ec4899"],
];

function gradientFor(seed: string): [string, string] {
  let hash = 0;
  for (let index = 0; index < seed.length; index += 1) {
    hash = (hash * 31 + seed.charCodeAt(index)) >>> 0;
  }
  return GRADIENTS[hash % GRADIENTS.length];
}

interface AvatarProps {
  name: string;
  src?: string | null;
  size?: "sm" | "md" | "lg" | "xl";
  online?: boolean;
  variant?: "user" | "group";
  className?: string;
}

export function Avatar({
  name,
  src,
  size = "md",
  online,
  variant = "user",
  className = "",
}: AvatarProps) {
  const [from, to] = gradientFor(name || "connecthub");
  return (
    <span
      className={`avatar avatar--${size} ${className}`}
      style={{ backgroundImage: `linear-gradient(135deg, ${from}, ${to})` }}
      aria-hidden="true"
    >
      {variant === "group" ? (
        <Icon name="users" size={size === "sm" ? 15 : size === "lg" ? 26 : 20} />
      ) : src ? (
        <img src={src} alt="" className="avatar__image" />
      ) : (
        <span className="avatar__initials">{initials(name)}</span>
      )}
      {online !== undefined && (
        <span
          className={`avatar__presence ${online ? "is-online" : "is-offline"}`}
        />
      )}
    </span>
  );
}
