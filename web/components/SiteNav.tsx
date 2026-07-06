import Link from "next/link";

interface SiteNavProps {
  active?: "dashboard" | "methodology";
}

export default function SiteNav({ active = "dashboard" }: SiteNavProps) {
  return (
    <header className="site-nav">
      <div className="site-nav-inner">
        <Link href="/" className="site-brand">
          Deforestation Detector
        </Link>
        <nav className="site-links" aria-label="Main">
          <Link
            href="/"
            className={active === "dashboard" ? "nav-link active" : "nav-link"}
          >
            Dashboard
          </Link>
          <Link
            href="/methodology"
            className={
              active === "methodology" ? "nav-link active" : "nav-link"
            }
          >
            Methodology
          </Link>
        </nav>
      </div>
    </header>
  );
}
