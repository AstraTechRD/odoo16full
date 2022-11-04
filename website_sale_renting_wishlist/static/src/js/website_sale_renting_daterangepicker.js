/** @odoo-module **/

import WebsiteSaleDaterangePicker from '@website_sale_renting/js/website_sale_renting_daterangepicker';

WebsiteSaleDaterangePicker.include({

    /**
     * Get product id and fall back on wishlist product id if it applies.
     *
     * @override
     */
    _getProductId() {
        let productId = this._super(...arguments) || this.productId;
        if (!productId && this.el.classList.contains('o_wish_daterangepicker')) {
            const tr = this.el.closest('tr');
            productId = tr && parseInt(tr.dataset.productId);
        }
        this.productId = productId;
        return productId;
    },

    _getParentElement() {
        if (this.el.classList.contains('o_wish_daterangepicker')) {
            return this.el.closest('tr[data-wish-id]');
        }
        return this._super(...arguments);
    },

});
