odoo.define('pos_iot.ProductScreen', function(require) {
    'use strict';

    const { Gui } = require('point_of_sale.Gui');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const Registries = require('point_of_sale.Registries');

    const PosIotProductScreen = ProductScreen =>
        class extends ProductScreen {
            get isScaleAvailable() {
                return super.isScaleAvailable && Boolean(this.env.proxy.iot_device_proxies.scale);
            }
            async _onScaleNotAvailable() {
                await Gui.showPopup('ErrorPopup', {
                    title: this._env._t('No Scale Detected'),
                    body: this._env._t(
                        'It seems that no scale was detected.\nMake sure that the scale is connected and visible in the IoT app.'
                    ),
                });
            }
        };

    Registries.Component.extend(ProductScreen, PosIotProductScreen);

    return ProductScreen;
});
