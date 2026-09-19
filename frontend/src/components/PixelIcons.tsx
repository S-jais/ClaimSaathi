import React from "react";

export function PixelLogo({ size = 28, className = "" }: { size?: number; className?: string }) {
  return null;
}

export function PixelArrowRight({ size = 18, className = "" }: { size?: number; className?: string }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 30 30"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden="true"
    >
      <path d="M12.9995 25H8.99951V21H12.9995V25Z" fill="currentColor" />
      <path d="M16.9995 21H12.9995V17H16.9995V21Z" fill="currentColor" />
      <path d="M20.9995 17H16.9995V13H20.9995V17Z" fill="currentColor" />
      <path d="M16.9995 13H12.9995V9H16.9995V13Z" fill="currentColor" />
      <path d="M12.9995 9H8.99951V5H12.9995V9Z" fill="currentColor" />
    </svg>
  );
}

export function PixelArrowLeft({ size = 18, className = "" }: { size?: number; className?: string }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 30 30"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden="true"
    >
      <path d="M16.9995 5L20.9995 5V9L16.9995 9L16.9995 5Z" fill="currentColor" />
      <path d="M12.9995 9L16.9995 9V13L12.9995 13L12.9995 9Z" fill="currentColor" />
      <path d="M8.99951 13H12.9995L12.9995 17L8.99951 17L8.99951 13Z" fill="currentColor" />
      <path d="M12.9995 17H16.9995L16.9995 21H12.9995L12.9995 17Z" fill="currentColor" />
      <path d="M16.9995 21H20.9995L20.9995 25H16.9995V21Z" fill="currentColor" />
    </svg>
  );
}

export function PixelChevronDown({ size = 18, className = "" }: { size?: number; className?: string }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 30 30"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden="true"
    >
      <path d="M4.99951 13L4.99951 9L8.99951 9L8.99951 13L4.99951 13Z" fill="currentColor" />
      <path d="M8.99951 17L8.99951 13H12.9995V17L8.99951 17Z" fill="currentColor" />
      <path d="M12.9995 21L12.9995 17H16.9995V21H12.9995Z" fill="currentColor" />
      <path d="M16.9995 17V13H20.9995V17H16.9995Z" fill="currentColor" />
      <path d="M20.9995 13V9L24.9995 9V13H20.9995Z" fill="currentColor" />
    </svg>
  );
}

export function PixelMenu({ size = 18, className = "" }: { size?: number; className?: string }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 30 30"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden="true"
    >
      <path d="M8.4 26H4V21.6H8.4V26Z" fill="currentColor" />
      <path d="M17.2 26H12.8V21.6H17.2V26Z" fill="currentColor" />
      <path d="M26 26H21.6V21.6H26V26Z" fill="currentColor" />
      <path d="M8.4 17.2H4V12.8H8.4V17.2Z" fill="currentColor" />
      <path d="M17.2 17.2H12.8V12.8H17.2V17.2Z" fill="currentColor" />
      <path d="M26 17.2H21.6V12.8H26V17.2Z" fill="currentColor" />
      <path d="M8.4 8.4H4V4H8.4V8.4Z" fill="currentColor" />
      <path d="M17.2 8.4H12.8V4H17.2V8.4Z" fill="currentColor" />
      <path d="M26 8.4H21.6V4H26V8.4Z" fill="currentColor" />
    </svg>
  );
}

export function PixelClose({ size = 18, className = "" }: { size?: number; className?: string }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 30 30"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden="true"
    >
      <path d="M8.4 26H4V21.6H8.4V26Z" fill="currentColor" />
      <path d="M26 26H21.6V21.6H26V26Z" fill="currentColor" />
      <path d="M12.8 21.6H8.4V17.2H12.8V21.6Z" fill="currentColor" />
      <path d="M21.6 21.6H17.2V17.2H21.6V21.6Z" fill="currentColor" />
      <path d="M17.2 17.2H12.8V12.8H17.2V17.2Z" fill="currentColor" />
      <path d="M12.8 12.8H8.4V8.4H12.8V12.8Z" fill="currentColor" />
      <path d="M21.6 12.8H17.2V8.4H21.6V12.8Z" fill="currentColor" />
      <path d="M8.4 8.4H4V4H8.4V8.4Z" fill="currentColor" />
      <path d="M26 8.4H21.6V4H26V8.4Z" fill="currentColor" />
    </svg>
  );
}

export function PixelCheck({ size = 18, className = "" }: { size?: number; className?: string }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden="true"
    >
      <rect x="18" y="5" width="3" height="3" fill="currentColor" />
      <rect x="15" y="8" width="3" height="3" fill="currentColor" />
      <rect x="12" y="11" width="3" height="3" fill="currentColor" />
      <rect x="9" y="14" width="3" height="3" fill="currentColor" />
      <rect x="6" y="11" width="3" height="3" fill="currentColor" />
      <rect x="3" y="8" width="3" height="3" fill="currentColor" />
    </svg>
  );
}

export function PixelAlert({ size = 18, className = "" }: { size?: number; className?: string }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden="true"
    >
      <rect x="10.5" y="4" width="3" height="9" fill="currentColor" />
      <rect x="10.5" y="16" width="3" height="3" fill="currentColor" />
    </svg>
  );
}

export function PixelSun({ size = 18, className = "" }: { size?: number; className?: string }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden="true"
    >
      <rect x="10" y="1" width="4" height="3" fill="currentColor" />
      <rect x="10" y="20" width="4" height="3" fill="currentColor" />
      <rect x="1" y="10" width="3" height="4" fill="currentColor" />
      <rect x="20" y="10" width="3" height="4" fill="currentColor" />
      <rect x="7" y="7" width="10" height="10" fill="currentColor" />
    </svg>
  );
}

export function PixelMoon({ size = 18, className = "" }: { size?: number; className?: string }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden="true"
    >
      <path
        d="M19 14H16V17H13V19H9V17H6V14H4V9H6V6H9V4H13V6H14V9H17V10H19V14Z"
        fill="currentColor"
      />
    </svg>
  );
}
