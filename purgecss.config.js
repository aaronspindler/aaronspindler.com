module.exports = {
  content: [
    'templates/**/*.html',
    'static/js/**/*.js',
    'blog/templates/**/*.html',
    'pages/templates/**/*.html',
    'accounts/templates/**/*.html'
  ],
  css: ['static/css/**/*.css'],
  defaultExtractor: content => {
    // Capture as liberally as possible, including things like `h-(screen-1.5)`
    const broadMatches = content.match(/[^<>"'`\s]*[^<>"'`\s:]/g) || []

    // Capture classes within other delimiters like .block(class="w-1/2") in Pug
    const innerMatches = content.match(/[^<>"'`\s.()]*[^<>"'`\s.():]/g) || []

    return broadMatches.concat(innerMatches)
  },
  safelist: {
    standard: [
      // Django-specific classes
      'errorlist',
      'helptext', 
      'required',
      'messages',
      'message',
      'error',
      'warning',
      'info',
      'success',
      // Dynamic classes that might be added via JS
      'active',
      'open',
      'show',
      'hidden',
      'visible',
      'collapsed',
      'expanded',
      // Form-related
      'invalid',
      'valid',
      'disabled',
      'readonly',
      // Keep all vendor prefixes
      /^-webkit-/,
      /^-moz-/,
      /^-ms-/,
      /^-o-/
    ],
    deep: [
      // Deep scan for dynamically generated classes
      /hljs-/,
      /kg-/,
      /photo-/,
      /book-/,
      /gallery-/
    ],
    greedy: [
      // Aggressively keep animation/transition related
      /transition/,
      /animation/,
      /transform/
    ]
  },
  blocklist: [
    // Remove development-only classes if any
    'debug',
    'test'
  ],
  keyframes: true,
  fontFace: true,
  variables: true,
  rejected: false // Set to true to see what's being removed
}