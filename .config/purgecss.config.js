module.exports = {
  content: [
    // Global templates
    'templates/**/*.html',
    // App-specific templates
    'blog/templates/**/*.html',
    'pages/templates/**/*.html',
    'accounts/templates/**/*.html',
    'photos/templates/**/*.html',
    'feefifofunds/templates/**/*.html',
    'projects/templates/**/*.html',
    'utils/templates/**/*.html',
    'omas/templates/**/*.html',
    // JavaScript files that might have dynamic classes
    'static/js/**/*.js',
    'omas/static/**/*.js',
    // Python files that might have class names in strings
    '**/*.py'
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
      'messages-container',
      'message',
      'message-text',
      'message-close',
      'message-success',
      'message-info',
      'message-warning',
      'message-error',
      'message-danger',
      'message-debug',
      'error',
      'warning',
      'info',
      'success',
      'debug',
      'danger',
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
      // Category bubble classes
      'category-tech',
      'category-personal',
      'category-projects',
      'category-guides',
      'category-smart_home',
      'category-reviews',
      'category-uncategorized',
      // Theme toggle classes
      'theme-toggle-container',
      'theme-toggle-btn',
      'theme-light',
      'theme-dark',
      'theme-auto',
      'theme-transition',
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
    // Note: 'debug' removed from blocklist as it's used for message-debug
    'test'
  ],
  keyframes: true,
  fontFace: true,
  variables: true,
  rejected: false // Set to true to see what's being removed
}
