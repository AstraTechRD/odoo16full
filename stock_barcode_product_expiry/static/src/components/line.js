/** @odoo-module **/

import LineComponent from '@stock_barcode/components/line';
import { patch } from 'web.utils';

patch(LineComponent.prototype, 'stock_barcode_product_expiry', {
    get isUseExpirationDate() {
        return this.line.product_id.use_expiration_date;
    },

    get expirationDate() {
        const dateTimeStrUTC = (this.line.lot_id && this.line.lot_id.expiration_date) || this.line.expiration_date;
        if (!dateTimeStrUTC) {
            return '';
        }
        const dateTimeStrLocal = moment.utc(dateTimeStrUTC).local().format('YYYY-MM-DD');
        return new Date(dateTimeStrLocal).toLocaleDateString();
    },
});
