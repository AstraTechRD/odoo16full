/** @odoo-module **/

import LazyBarcodeCache from '@stock_barcode/lazy_barcode_cache';

import {patch} from 'web.utils';

patch(LazyBarcodeCache.prototype, 'stock_barcode_picking_batch', {
    /**
     * @override
     */
     _constructor() {
        this._super(...arguments);
        this.barcodeFieldByModel['stock.picking.batch'] = 'name';
    },
});
