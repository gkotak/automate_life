import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
    subsets: ["latin"],
    variable: "--font-inter",
    display: "swap",
});

export const metadata: Metadata = {
    title: "Moderator1 - Add the depth of an interview to every survey you send out.",
    description: "Follow up with an AI-moderated interviews with each respondent about their survey responses.",
};

export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <html lang="en">
            <body className={`${inter.variable} antialiased font-sans`}>
                {children}
            </body>
        </html>
    );
}
