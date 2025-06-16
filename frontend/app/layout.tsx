import React from 'react'
import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'AI Chat - Llama 3.2 Models',
  description: 'Chat with powerful Llama 3.2 MOE models',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <head>
        <script src="/fix-mime.js" type="application/javascript"></script>
      </head>
      <body className="font-sans antialiased">
        {children}
      </body>
    </html>
  )
} 