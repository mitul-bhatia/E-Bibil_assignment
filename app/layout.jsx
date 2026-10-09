import { DM_Sans } from 'next/font/google';
import './globals.css';

const font = DM_Sans({ subsets: ['latin'], display: 'swap' });
export const metadata = { title: 'Source — Client Knowledge Assistant', description: 'Ask about Automattic policies. Read the answer and its original sources.' };

export default function RootLayout({ children }) {
  return <html lang="en"><body className={font.className}>{children}</body></html>;
}
