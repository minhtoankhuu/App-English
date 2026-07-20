import type { ReactNode } from "react";

function Svg({ children }: { children: ReactNode }) {
  return (
    <svg className="icon" viewBox="0 0 24 24" aria-hidden="true">
      {children}
    </svg>
  );
}

export function BrandLogoIcon({ size = 24 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 28 28"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <path
        d="M6.5 7.5C8.8 6.5 11.5 6.8 14 8C16.5 6.8 19.2 6.5 21.5 7.5V21.5C19.2 20.5 16.5 20.8 14 22C11.5 20.8 8.8 20.5 6.5 21.5V7.5Z"
        stroke="currentColor"
        strokeWidth="2.1"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="rgba(255, 255, 255, 0.18)"
      />
      <path
        d="M14 8V22"
        stroke="currentColor"
        strokeWidth="2.1"
        strokeLinecap="round"
      />
      <path
        d="M21.5 3L22.2 4.8L24 5.5L22.2 6.2L21.5 8L20.8 6.2L19 5.5L20.8 4.8L21.5 3Z"
        fill="#60a5fa"
      />
      <path
        d="M7 3.5L7.4 4.5L8.4 4.9L7.4 5.3L7 6.3L6.6 5.3L5.6 4.9L6.6 4.5L7 3.5Z"
        fill="#bfdbfe"
      />
    </svg>
  );
}

export function PlusIcon() {
  return (
    <Svg>
      <path d="M12 5v14M5 12h14" />
    </Svg>
  );
}

export function PencilIcon() {
  return (
    <Svg>
      <path d="M4 20l4-1L20 7l-3-3L5 16l-1 4z" />
      <path d="M14 6l3 3" />
    </Svg>
  );
}

export function DocIcon() {
  return (
    <Svg>
      <path d="M7 3h7l5 5v13H7z" />
      <path d="M14 3v5h5M10 13h5M10 17h5" />
    </Svg>
  );
}

export function LayersIcon() {
  return (
    <Svg>
      <path d="M12 3l9 5-9 5-9-5 9-5z" />
      <path d="M3 13l9 5 9-5" />
    </Svg>
  );
}

export function UsersIcon() {
  return (
    <Svg>
      <circle cx="9" cy="8" r="3.4" />
      <path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6" />
      <circle cx="17" cy="9" r="2.4" />
      <path d="M16.5 14.6c2.6.5 4.5 2.7 4.5 5.4" />
    </Svg>
  );
}

export function BankIcon() {
  return (
    <Svg>
      <ellipse cx="12" cy="6" rx="7" ry="3" />
      <path d="M5 6v12c0 1.7 3.1 3 7 3s7-1.3 7-3V6M5 12c0 1.7 3.1 3 7 3s7-1.3 7-3" />
    </Svg>
  );
}

export function GearIcon() {
  return (
    <Svg>
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z" />
    </Svg>
  );
}
