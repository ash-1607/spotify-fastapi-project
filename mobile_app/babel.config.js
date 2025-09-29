module.exports = {
  presets: ['module:@react-native/babel-preset'],
  // --- ADD THIS PLUGINS SECTION ---
  plugins: [
    ["module:react-native-dotenv", {
      "moduleName": "@env",
      "path": ".env",
    }]
  ]
};
