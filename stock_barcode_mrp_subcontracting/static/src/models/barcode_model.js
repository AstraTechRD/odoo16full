/** @odoo-module **/

import BarcodeModel from '@stock_barcode/models/barcode_model';
import { patch } from 'web.utils';

patch(BarcodeModel.prototype, 'stock_barcode_mrp_subcontracting', {

    showSubcontractingDetails(line) {
        return false;
    },

    get displayActionRecordComponents() {
        return false;
    },
});
