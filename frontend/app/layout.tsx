import "./globals.css";

export const metadata = {
  title: "AI Time-Travel Explorer",
  description: "Cinematic reactive movie game prototype",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
