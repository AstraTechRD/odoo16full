/** @odoo-module **/

import { bus } from 'web.core';
import LineComponent from '@stock_barcode/components/line';
import { patch } from 'web.utils';

patch(LineComponent.prototype, 'stock_barcode_mrp_subcontracting', {
    async showSubcontractingDetails() {
        const {action, options} = await this.env.model._getActionSubcontractingDetails(this.line);
        options.on_close = function (ev) {
            if (ev === undefined) {
                this._onRefreshState.call(this, { lineId: this.props.id });
            }
        };
        await bus.trigger('do-action', {action, options});
    },
});
