"use client";

import Image from "next/image";
import Link from "next/link";
import { useState } from "react";
import { usePathname } from "next/navigation";
import { Menu, X } from "lucide-react";

export default function Header() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const pathname = usePathname();
  const isHomePage = pathname === "/";

  // Use relative anchors on home page, absolute paths elsewhere
  const getLink = (anchor: string) => (isHomePage ? anchor : `/${anchor}`);

  return (
    <nav className="navigation">
      <Link href="/" className="w-inline-block">
        <Image
          src="/images/Logo.avif"
          alt="Moderator1"
          width={140}
          height={32}
          className="logo"
        />
      </Link>

      {/* Desktop Menu */}
      <div className="menu hidden md:flex">
        <a href={getLink("#values")} className="nav-link">
          <div className="link-style">Value</div>
        </a>
        <a href={getLink("#how-it-works")} className="nav-link">
          <div className="link-style">How it works</div>
        </a>
        <a href={getLink("#use-cases")} className="nav-link">
          <div className="link-style">Use Cases</div>
        </a>
        <a href={getLink("#pricing")} className="nav-link">
          <div className="link-style">Pricing</div>
        </a>
      </div>

      <a
        href="https://calendly.com/moderator_1/demo_setup"
        target="_blank"
        rel="noopener noreferrer"
        className="button-secondary hidden md:flex"
      >
        <div className="button-style-3">Book a demo</div>
      </a>

      {/* Mobile Menu Button */}
      <button
        className="md:hidden p-2"
        onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
        aria-label="Toggle menu"
      >
        {mobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
      </button>

      {/* Mobile Menu */}
      {mobileMenuOpen && (
        <div className="mobile-menu md:hidden absolute top-full left-0 right-0 bg-white border border-gray-200 rounded-2xl mt-2 p-4 shadow-lg">
          <a href={getLink("#values")} className="nav-link block py-2" onClick={() => setMobileMenuOpen(false)}>
            <div className="link-style">Value</div>
          </a>
          <a href={getLink("#how-it-works")} className="nav-link block py-2" onClick={() => setMobileMenuOpen(false)}>
            <div className="link-style">How it works</div>
          </a>
          <a href={getLink("#use-cases")} className="nav-link block py-2" onClick={() => setMobileMenuOpen(false)}>
            <div className="link-style">Use Cases</div>
          </a>
          <a href={getLink("#pricing")} className="nav-link block py-2" onClick={() => setMobileMenuOpen(false)}>
            <div className="link-style">Pricing</div>
          </a>
          <a
            href="https://calendly.com/moderator_1/demo_setup"
            target="_blank"
            rel="noopener noreferrer"
            className="button-secondary mt-4 w-full justify-center"
          >
            <div className="button-style-3">Book a demo</div>
          </a>
        </div>
      )}
    </nav>
  );
}
