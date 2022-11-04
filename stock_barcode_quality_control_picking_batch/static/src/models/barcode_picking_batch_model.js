/** @odoo-module **/

import BarcodePickingBatchModel from '@stock_barcode_picking_batch/models/barcode_picking_batch_model';
import { patch } from 'web.utils';

patch(BarcodePickingBatchModel.prototype, 'stock_barcode_quality_control_picking_batch', {
    openQualityChecksMethod: 'action_open_quality_check_wizard',
});
