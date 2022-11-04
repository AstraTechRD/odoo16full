/** @odoo-module **/

import BarcodePickingModel from '@stock_barcode/models/barcode_picking_model';
import { patch } from 'web.utils';

patch(BarcodePickingModel.prototype, 'stock_barcode_quality_control', {
    openQualityChecksMethod: 'check_quality',

    get displayValidateButton() {
        return !(this.record && this.record.quality_check_todo) && this._super.apply(this, arguments);
    }
});
