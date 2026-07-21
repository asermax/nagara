// Open vs closed eye, stroked in currentColor so CSS drives colour + the scale drama.
export const EyeIcon = ({ open, size = 26 }: { open: boolean; size?: number }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth={1.8}
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden
  >
    {open ? (
      <>
        <path d="M1.5 12s4-7 10.5-7 10.5 7 10.5 7-4 7-10.5 7S1.5 12 1.5 12z" />
        <circle cx="12" cy="12" r="3.2" />
        {/* 8 lashes radiating evenly around the eye, offset from it for a wide-open look */}
        <path d="M20 5.1 21.7 3.6" />
        <path d="M15.2 3.3 15.9 1.4" />
        <path d="M8.8 3.3 8.1 1.4" />
        <path d="M4 5.1 2.3 3.6" />
        <path d="M4 18.9 2.3 20.4" />
        <path d="M8.8 20.7 8.1 22.6" />
        <path d="M15.2 20.7 15.9 22.6" />
        <path d="M20 18.9 21.7 20.4" />
      </>
    ) : (
      <>
        <path d="M2.5 10.5S6.5 16 12 16s9.5-5.5 9.5-5.5" />
        <path d="M4 14.5l-1.4 2" />
        <path d="M9 16.2l-.6 2.2" />
        <path d="M15 16.2l.6 2.2" />
        <path d="M20 14.5l1.4 2" />
      </>
    )}
  </svg>
);
