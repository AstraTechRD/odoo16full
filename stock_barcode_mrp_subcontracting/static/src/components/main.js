/** @odoo-module **/

import { bus } from 'web.core';
import MainComponent from '@stock_barcode/components/main';
import { patch } from 'web.utils';

patch(MainComponent.prototype, 'stock_barcode_mrp_subcontracting', {
    async recordComponents() {
        const {action, options} = await this.env.model._getActionRecordComponents();
        options.on_close = async (ev) => {
            if (ev === undefined) {
                await this._onRefreshState({ recordId: this.props.id });
                this.render(true);
            }
        };
        await bus.trigger('do-action', {action, options});
    },
});
