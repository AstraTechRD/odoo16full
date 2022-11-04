/** @odoo-module **/

import WebsiteSaleDaterangePicker from '@website_sale_renting/js/website_sale_renting_daterangepicker';

WebsiteSaleDaterangePicker.include({
    events: Object.assign({}, WebsiteSaleDaterangePicker.prototype.events, {
        'change_product_id': '_onChangeProductId',
    }),
    rentingAvailabilities: {},

    /**
     * Override to get the renting product stock availabilities
     *
     * @override
     */
    willStart: function () {
        return Promise.all([
            this._super.apply(this, arguments),
            this._updateRentingProductAvailabilities(),
        ]);
    },

    // ------------------------------------------
    // Handlers
    // ------------------------------------------
    /**
     * Handle product changed to update the availabilities
     *
     * @param {Event} _event
     * @param {object} params
     */
    _onChangeProductId(_event, params) {
        if (this.productId !== params.product_id) {
            this.productId = params.product_id;
            this._updateRentingProductAvailabilities();
        }
    },

    // ------------------------------------------
    // Utils
    // ------------------------------------------
    /**
     * Update the renting availabilities dict with the unavailabilities of the current product
     *
     * @private
     */
    async _updateRentingProductAvailabilities() {
        const productId = this._getProductId();
        if (!productId || this.rentingAvailabilities[productId]) {
            return;
        }
        return this._rpc({
            route: "/rental/product/availabilities",
            params: {
                product_id: productId,
                min_date: moment(),
                max_date: moment().add(3, 'y'),
            }
        }).then((result) => {
            if (result.renting_availabilities) {
                for (const interval of result.renting_availabilities) {
                    let utcDate = moment(interval.start);
                    interval.start = utcDate.add(this.getSession().getTZOffset(utcDate), 'minutes');
                    utcDate = moment(interval.end);
                    interval.end = utcDate.add(this.getSession().getTZOffset(utcDate), 'minutes');
                }
            }
            this.rentingAvailabilities[productId] = result.renting_availabilities || [];
            this.preparationTime = result.preparation_time;
            $('.oe_website_sale').trigger('renting_constraints_changed', {
                rentingAvailabilities: this.rentingAvailabilities,
                preparationTime: this.preparationTime,
            });
            this._verifyValidPeriod();
        });
    },

    /**
     * Override to invalid dates where the product is unavailable
     *
     * @param {moment} date
     */
    _isInvalidDate(date) {
        const result = this._super.apply(this, arguments);
        if (!result) {
            const productId = this._getProductId();
            if (!productId) {
                return false;
            }
            const dateStart = date.startOf('day');
            for (const interval of this.rentingAvailabilities[productId]) {
                if (interval.start.startOf('day') > dateStart) {
                    return false;
                }
                if (interval.end.endOf('day') > dateStart && interval.quantity_available <= 0) {
                    return true;
                }
            }
        }
        return result;
    },

    /**
     * Set Custom CSS to a given daterangepicker cell
     *
     * This function is used in the daterange picker objects and meant to be easily overriden.
     *
     * @param {moment} date
     * @private
     */
    _isCustomDate(date) {
        const result = this._super.apply(this, arguments);
        const productId = this._getProductId();
        if (!productId) {
            return;
        }
        const dateStart = date.startOf('day');
        for (const interval of this.rentingAvailabilities[productId]) {
            if (interval.start.startOf('day') > dateStart) {
                return result;
            }
            if (interval.end.endOf('day') > dateStart && interval.quantity_available <= 0) {
                result.push('o_daterangepicker_danger');
                return result;
            }
        }
        return result;
    },

    /**
     * Get the product id from the dom if not initialized.
     */
    _getProductId() {
        // cache this id a little bit ?
        this._super.apply(this, arguments);
        if (!this.productId) {
            const productSelector = [
                'input[type="hidden"][name="product_id"]',
                'input[type="radio"][name="product_id"]:checked'
            ];
            const form = this.el.closest('form');
            const productInput = form && form.querySelector(productSelector.join(', '));
            this.productId = productInput && parseInt(productInput.value);
        }
        return this.productId;
    },
});
