import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'cryptoterminal',
  description: 'Bitcoin-first trading analysis dashboard',
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
