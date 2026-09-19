import { Analytics } from '@vercel/analytics/next'
import type { Metadata, Viewport } from 'next'
import Script from 'next/script'
import './globals.css'

export const metadata: Metadata = {
  title: 'StatArb N50 | Quant Research Terminal',
  description: 'Institutional-grade cointegration research and statistical arbitrage analytics for the Nifty 50.',
  icons: {
    icon: [
      {
        url: '/icon-dark-32x32.png',
        type: 'image/png',
      },
    ],
    apple: '/icon-dark-32x32.png',
  },
}

export const viewport: Viewport = {
  colorScheme: 'light dark',
  themeColor: '#0a0a0a',
}

const themeScript = `(function(){try{var t=localStorage.getItem('statarb-theme');if(t==='dark'||t==='light'){document.documentElement.setAttribute('data-theme',t);}else{document.documentElement.setAttribute('data-theme','light');}}catch(e){document.documentElement.setAttribute('data-theme','light');}})();`

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" data-theme="light" suppressHydrationWarning>
      <head>
        <Script
          id="statarb-theme-init"
          strategy="beforeInteractive"
          dangerouslySetInnerHTML={{ __html: themeScript }}
        />
      </head>
      <body className="antialiased" suppressHydrationWarning>
        {children}
        {process.env.NODE_ENV === 'production' && <Analytics />}
      </body>
    </html>
  )
}
