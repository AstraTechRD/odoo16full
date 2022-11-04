/** @odoo-module **/

import publicWidget from 'web.public.widget';
import 'website_sale_comparison.comparison';
import { RentingMixin } from '@website_sale_renting/js/renting_mixin';

publicWidget.registry.ProductComparison.include(RentingMixin);
publicWidget.registry.ProductComparison.include({

    /**
     * Get the addToCart params with renting params
     *
     * @param {number} productId
     * @param {JQuery} $form
     * @override
     */
    _getAddToCartParams(productId, $form) {
        const params = this._super.apply(this, arguments);
        const isRental = $form.find('input[name=is_rental]');
        if (isRental.val()) {
            Object.assign(params, this._getRentingDates($form));
        }
        return params;
    },

});
