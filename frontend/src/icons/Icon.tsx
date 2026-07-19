import type { ReactNode } from "react";

function Svg({ children }: { children: ReactNode }) {
  return (
    <svg className="icon" viewBox="0 0 24 24" aria-hidden="true">
      {children}
    </svg>
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
