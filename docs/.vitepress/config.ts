import { defineConfig } from 'vitepress'

export default defineConfig({
  lang: 'en-US',
  title: 'occam-gitignore',
  description: 'Deterministic .gitignore generation. Zero latency. Reproducible.',
  base: '/gitignore/',
  cleanUrls: true,
  lastUpdated: true,
  ignoreDeadLinks: 'localhostLinks',

  markdown: {
    languageAlias: { gitignore: 'bash' },
  },

  head: [
    // Tutto first-party. 'unsafe-inline' serve perche' VitePress emette
    // uno script inline per il tema e stili inline.
    [
      'meta',
      {
        'http-equiv': 'Content-Security-Policy',
        content:
          "default-src 'self'; script-src 'self' 'unsafe-inline'; " +
          "style-src 'self' 'unsafe-inline'; img-src 'self' data:; " +
          "font-src 'self'; connect-src 'self'; base-uri 'self'; form-action 'self'",
      },
    ],
    ['meta', { name: 'theme-color', content: '#0a0a0a' }],
    ['meta', { property: 'og:title', content: 'occam-gitignore' }],
    ['meta', { property: 'og:description', content: 'Deterministic .gitignore generation.' }],
    ['meta', { property: 'og:type', content: 'website' }],
  ],

  themeConfig: {
    siteTitle: 'occam-gitignore',
    nav: [
      { text: 'Guide', link: '/guide/getting-started', activeMatch: '/guide/' },
      { text: 'Reference', link: '/reference/core', activeMatch: '/reference/' },
      { text: 'Benchmark', link: '/guide/benchmark' },
      {
        text: 'v0.1.3',
        items: [
          { text: 'Changelog', link: 'https://github.com/fabriziosalmi/gitignore/blob/main/CHANGELOG.md' },
          { text: 'Releases', link: 'https://github.com/fabriziosalmi/gitignore/releases' },
          { text: 'Contributing', link: '/guide/contributing' },
        ],
      },
    ],

    sidebar: {
      '/guide/': [
        {
          text: 'Introduction',
          items: [
            { text: 'Getting started', link: '/guide/getting-started' },
            { text: 'Why deterministic?', link: '/guide/why-deterministic' },
            { text: 'Architecture', link: '/guide/architecture' },
          ],
        },
        {
          text: 'Concepts',
          items: [
            { text: 'Determinism contract', link: '/guide/determinism' },
            { text: 'Fingerprinting', link: '/guide/fingerprinting' },
            { text: 'Rules table', link: '/guide/rules-table' },
            { text: 'Provenance', link: '/guide/provenance' },
          ],
        },
        {
          text: 'Adapters',
          items: [
            { text: 'CLI', link: '/guide/cli' },
            { text: 'HTTP API', link: '/guide/api' },
            { text: 'MCP server', link: '/guide/mcp' },
          ],
        },
        {
          text: 'Quality',
          items: [
            { text: 'Benchmark methodology', link: '/guide/benchmark' },
            { text: 'Training pipeline', link: '/guide/training' },
            { text: 'Contributing', link: '/guide/contributing' },
          ],
        },
      ],
      '/reference/': [
        {
          text: 'Reference',
          items: [
            { text: 'Core API', link: '/reference/core' },
            { text: 'Schema', link: '/reference/schema' },
            { text: 'Ports', link: '/reference/ports' },
            { text: 'CLI flags', link: '/reference/cli' },
            { text: 'HTTP endpoints', link: '/reference/http' },
            { text: 'MCP tools', link: '/reference/mcp' },
          ],
        },
      ],
    },

    socialLinks: [
      { icon: 'github', link: 'https://github.com/fabriziosalmi/gitignore' },
    ],

    footer: {
      message: 'Released under the MIT License.' + ' · <a href="https://fabriziosalmi.github.io/privacy">Privacy &amp; legal</a>',
      copyright: 'Copyright © 2026 Fabrizio Salmi',
    },

    search: { provider: 'local' },

    editLink: {
      pattern: 'https://github.com/fabriziosalmi/gitignore/edit/main/docs/:path',
      text: 'Edit this page on GitHub',
    },

    outline: { level: [2, 3] },
  },
})
