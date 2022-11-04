/** @odoo-module **/

import BarcodePickingBatchModel from '@stock_barcode_picking_batch/models/barcode_picking_batch_model';
import MainComponent from '@stock_barcode/components/main';
import OptionLine from '@stock_barcode_picking_batch/components/option_line';

import { patch } from 'web.utils';

patch(MainComponent.prototype, 'stock_barcode_picking_batch', {
    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    confirm: function (ev) {
        ev.stopPropagation();
        this.env.model.confirmSelection();
    },

    get displayHeaderInfoAsColumn() {
        return this._super() || this.isConfiguring || !this.env.model.canBeProcessed;
    },

    async exit(ev) {
        if (this.displayBarcodeLines && this.env.model.needPickings && !this.env.model.needPickingType && this.env.model.pickingTypes) {
            this.env.model.record.picking_type_id = false;
            return this.env.model.trigger('update');
        }
        return await this._super(...arguments);
    },

    get isConfiguring() {
        return this.env.model.needPickingType || this.env.model.needPickings;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _getModel: function (params) {
        const { rpc, notification, orm } = this;
        if (params.model === 'stock.picking.batch') {
            return new BarcodePickingBatchModel(params, { rpc, notification, orm });
        }
        return this._super(...arguments);
    },
});

MainComponent.components.OptionLine = OptionLine;
