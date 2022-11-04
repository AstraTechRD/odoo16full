/** @odoo-module **/

import WebsiteSaleDaterangePicker from '@website_sale_renting/js/website_sale_renting_daterangepicker';

WebsiteSaleDaterangePicker.include({

    /**
     * Get product id and fall back on comparison product id if it applies.
     *
     * @override
     */
    _getProductId() {
        this._super.apply(this, arguments);
        if (!this.productId && this.el.classList.contains('o_comparison_daterangepicker')) {
            const form = this.el.closest('form');
            const input = form && form.querySelector("input[name=product_id]");
            this.productId = input && parseInt(input.value);
        }
        return this.productId;
    },

});
