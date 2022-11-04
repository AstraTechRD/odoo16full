/** @odoo-module **/

import BarcodePickingModel from '@stock_barcode/models/barcode_picking_model';
import { patch } from 'web.utils';

patch(BarcodePickingModel.prototype, 'stock_barcode_product_expiry', {

    async updateLine(line, args) {
        this._super(...arguments);
        if (args.expiration_date) {
            line.expiration_date = args.expiration_date;
        }
    },

    async _processGs1Data(data) {
        const result = {};
        const { rule, value } = data;
        if (rule.type === 'expiration_date') {
            // convert to noon to avoid most timezone issues
            value.setHours(12, 0, 0);
            result.expirationDate = moment.utc(value).format('YYYY-MM-DD HH:mm:ss');
            result.match = true;
        } else if (rule.type === 'use_date') {
            result.useDate = value;
            result.match = true;
        } else {
            return await this._super(...arguments);
        }
        return result;
    },

    async _parseBarcode(barcode, filters) {
        const barcodeData = await this._super(...arguments);
        const {product, useDate, expirationDate} = barcodeData;
        if (product && useDate && !expirationDate) {
            const value = new Date(useDate);
            value.setDate(useDate.getDate() + product.use_time);
            // convert to noon to avoid most timezone issues
            value.setHours(12, 0, 0);
            barcodeData.expirationDate = moment.utc(value).format('YYYY-MM-DD HH:mm:ss');
        }
        return barcodeData;
    },

    _convertDataToFieldsParams(args) {
        const params = this._super(...arguments);
        if (args.expirationDate) {
            params.expiration_date = args.expirationDate;
        }
        return params;
    },

    _getFieldToWrite() {
        const fields = this._super(...arguments);
        fields.push('expiration_date');
        return fields;
    },

    _createCommandVals(line) {
        const values = this._super(...arguments);
        values.expiration_date = line.expiration_date;
        return values;
    },
});
