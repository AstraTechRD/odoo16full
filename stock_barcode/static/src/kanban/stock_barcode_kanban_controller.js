/** @odoo-module */

import { KanbanController } from '@web/views/kanban/kanban_controller';
import { bus } from 'web.core';

const { onMounted, onWillUnmount } = owl;

export class StockBarcodeKanbanController extends KanbanController {
    setup() {
        super.setup(...arguments);
        onMounted(() => {
            bus.on('barcode_scanned', this, this._onBarcodeScannedHandler);
            document.activeElement.blur();
        });
        onWillUnmount(() => {
            bus.off('barcode_scanned', this, this._onBarcodeScannedHandler);
        });
    }

    openRecord(record) {
        this.actionService.doAction('stock_barcode.stock_barcode_picking_client_action', {
            additionalContext: { active_id: record.resId },
        });
    }

    async createRecord() {
        const action = await this.model.orm.call(
            'stock.picking',
            'action_open_new_picking',
            [], { context: this.props.context }
        );
        if (action) {
            return this.actionService.doAction(action);
        }
        return super.createRecord(...arguments);
    }

    // --------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when the user scans a barcode.
     *
     * @param {String} barcode
     */
    async _onBarcodeScannedHandler(barcode) {
        if (this.props.resModel != 'stock.picking') {
            return;
        }
        const kwargs = { barcode, context: this.props.context };
        const res = await this.model.orm.call(this.props.resModel, 'filter_on_barcode', [], kwargs);
        if (res.action) {
            this.actionService.doAction(res.action);
        } else if (res.warning) {
            const params = { title: res.warning.title, type: 'danger' };
            this.model.notificationService.add(res.warning.message, params);
        }
    }
}
