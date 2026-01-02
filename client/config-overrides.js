const { override, useBabelRc } = require('customize-cra');
const path = require('path');

module.exports = override(
    useBabelRc(),

    // Add alias
    (config) => {
        config.resolve.alias = {
            ...config.resolve.alias,
            '~': path.resolve(__dirname, 'src'),
        };
        return config;
    },

    // Fix Invalid Host Header
    (config) => {
        if (!config.devServer) config.devServer = {};
        config.devServer.disableHostCheck = true;
        config.devServer.host = '0.0.0.0';
        return config;
    },
);
