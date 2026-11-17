/** Brand mark: a statement sheet with one highlighted row. Mirrors marketing/src/components/LogoMark.astro. */
export default function LogoMark({ size = 28, className }) {
  return (
    <svg className={className} width={size} height={size} viewBox="0 0 32 32" aria-hidden="true" focusable="false">
      <rect x="5" y="2.5" width="22" height="27" rx="1.5" fill="#fff" stroke="#141414" strokeWidth="2.2" />
      <rect x="7.5" y="13" width="17" height="5" fill="#ffe34d" />
      <path d="M9.5 8h13M9.5 15.5h13M9.5 23h9" stroke="#141414" strokeWidth="2.2" strokeLinecap="square" />
    </svg>
  );
}
