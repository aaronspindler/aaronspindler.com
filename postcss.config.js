module.exports = {
  plugins: [
    require('postcss-import')({
      path: ['static/css']
    }),
    require('postcss-preset-env')({
      stage: 2,
      autoprefixer: {
        grid: 'autoplace'
      }
    }),
    require('autoprefixer')({
      overrideBrowserslist: ['> 0.5%', 'last 2 versions', 'not dead', 'not op_mini all'],
      grid: 'autoplace'
    }),
    require('cssnano')({
      preset: ['advanced', {
        discardComments: {
          removeAll: true
        },
        normalizeWhitespace: true,
        minifyFontValues: true,
        minifySelectors: true,
        mergeLonghand: true,
        mergeRules: true,
        minifyGradients: true,
        convertValues: {
          length: true,
          time: true,
          angle: true,
          precision: 3
        },
        reduceTransforms: true,
        discardUnused: true,
        discardDuplicates: true,
        discardEmpty: true,
        uniqueSelectors: true,
        cssDeclarationSorter: {
          order: 'smacss'
        },
        calc: {
          precision: 3
        },
        colormin: true,
        ordered: true,
        autoprefixer: false,
        mergeIdents: true,
        reduceIdents: true,
        zindex: true,
        svgo: true,
        normalizeUrl: true,
        normalizePositions: true,
        normalizeDisplayValues: true,
        normalizeTimingFunctions: true,
        normalizeCharset: true,
        minifyParams: true,
        orderedValues: true,
        rawCache: true
      }]
    })
  ]
}