/** @odoo-module */

import { patch } from 'web.utils';
import { RentalConfiguratorRecord } from "@sale_renting/js/rental_configurator_model";

/**
 * This model is overridden to allow configuring sale_order_lines through a popup
 * window when a product with 'rent_ok' is selected.
 *
 */
patch(RentalConfiguratorRecord.prototype, 'sale_stock_renting', {

    _getRentalInfos() {
        const rentalInfos = this._super();
        rentalInfos.reserved_lot_ids = {
          operation: 'MULTI',
          commands: [
            {operation: 'DELETE_ALL'},
            {operation: 'ADD_M2M', ids: this.data.lot_ids.currentIds.map(
                (lotId) => { return {id: lotId}; }
            )},
          ],
        };
        return rentalInfos;
    },
});
