const path = require("path");

module.exports = {
  webpack: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
    configure: (config) => {
      // TalkingHead can load lip-sync languages with a runtime-computed import().
      // We never use that path (Avatar3D registers English directly), so its
      // "Critical dependency" warning is noise, and CI builds treat warnings as errors.
      config.ignoreWarnings = [
        ...(config.ignoreWarnings || []),
        { module: /@met4citizen[\\/]talkinghead/, message: /Critical dependency/ },
      ];
      return config;
    },
  },
};
