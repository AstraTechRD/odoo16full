/** @odoo-module */

import { KanbanRenderer } from '@web/views/kanban/kanban_renderer';
import { useService } from '@web/core/utils/hooks';

const { onWillStart } = owl;

export class StockBarcodeKanbanRenderer extends KanbanRenderer {
    setup() {
        super.setup(...arguments);
        const user = useService('user');
        this.display_protip = this.props.list.resModel === 'stock.picking';
        onWillStart(async () => {
            this.packageEnabled = await user.hasGroup('stock.group_tracking_lot');
        });
    }
}
StockBarcodeKanbanRenderer.template = 'stock_barcode.KanbanRenderer';
