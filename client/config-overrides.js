const { override, useBabelRc } = require('customize-cra');

module.exports = override(
    // eslint-disable-next-line react-hooks/rules-of-hooks
    useBabelRc(),
);

const path = require('path');

module.exports = function override(config, env) {
    config.resolve.alias = {
        '~': path.resolve(__dirname, 'src'),
    };
    return config;
};
