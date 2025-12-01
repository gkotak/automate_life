import type { Metadata } from "next";
import { Inter, PT_Serif } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const ptSerif = PT_Serif({
  subsets: ["latin"],
  weight: ["400", "700"],
  variable: "--font-pt-serif",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Moderator1 - AI-Moderated Follow-up Interviews",
  description: "Replace open-ended survey questions with AI-moderated voice interviews. Boost completion rates and get deeper insights.",
  keywords: ["survey", "AI", "interviews", "feedback", "voice", "moderation"],
  openGraph: {
    title: "Moderator1 - AI-Moderated Follow-up Interviews",
    description: "Replace open-ended survey questions with AI-moderated voice interviews.",
    type: "website",
    url: "https://www.moderator1.com",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${inter.variable} ${ptSerif.variable}`}>
      <body>
        {children}
      </body>
    </html>
  );
}
