import Header from "./Header";
import Footer from "./Footer";

interface LegalPageLayoutProps {
  title: string;
  lastUpdated: string;
  children: React.ReactNode;
}

export default function LegalPageLayout({
  title,
  lastUpdated,
  children,
}: LegalPageLayoutProps) {
  return (
    <div className="body">
      <Header />

      {/* Content */}
      <main className="legal-content">
        <article className="legal-article">
          <h1 className="legal-title">
            {title}
          </h1>
          <p className="legal-updated">
            Last updated: {lastUpdated}
          </p>
          <div className="legal-prose">{children}</div>
        </article>
      </main>

      <Footer />
    </div>
  );
}
