odoo.define('l10n_de_pos_cert.ProductScreen', function(require) {
    "use strict";

    const ProductScreen = require('point_of_sale.ProductScreen');
    const Registries = require('point_of_sale.Registries');
    const { TaxError } = require('l10n_de_pos_cert.errors');

    const PosDeProductScreen = ProductScreen => class extends ProductScreen {
        //@Override
        async _clickProduct(event) {
            try {
                await super._clickProduct(...arguments)
            } catch (error) {
                if (this.env.pos.isCountryGermanyAndFiskaly() && error instanceof TaxError) {
                    await this._showTaxError()
                } else {
                    throw error;
                }
            }
        }
        //@Override
        async _barcodeProductAction(code) {
            try {
                await super._barcodeProductAction(...arguments);
            } catch(error) {
                if (this.env.pos.isCountryGermanyAndFiskaly() && error instanceof TaxError) {
                    await this._showTaxError()
                } else {
                    throw error;
                }
            }
        }
        async _showTaxError() {
            const rates = Object.keys(this.env.pos.vatRateMapping);
            const title = this.env._t('Tax error');
            let body;
            if (rates.length) {
                const ratesText = [rates.slice(0,-1).join(', '), rates.slice(-1)[0]].join(' and ');
                body = _.str.sprintf(this.env._t(
                    'Product has an invalid tax amount. Only the following rates are allowed: %s.'
                ), ratesText);
            } else {
                body = this.env._t('There was an error while loading the Germany taxes. Try again later or your Fiskaly API key and secret might have been corrupted, request new ones')
            }
            await this.showPopup('ErrorPopup', { title, body });
        }

    }

    Registries.Component.extend(ProductScreen, PosDeProductScreen);

    return ProductScreen;
});
