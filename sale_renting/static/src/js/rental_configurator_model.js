/** @odoo-module */
import { registry } from "@web/core/registry";
import { formView } from "@web/views/form/form_view"
import { Record, RelationalModel } from "@web/views/relational_model";

/**
 * This model is overridden to allow configuring sale_order_lines through a popup
 * window when a product with 'rent_ok' is selected.
 *
 */
export class RentalConfiguratorRelationalModel extends RelationalModel {}

export class RentalConfiguratorRecord extends Record {

    _getRentalInfos() {
        return {
            start_date: this.data.pickup_date,
            return_date: this.data.return_date,
            price_unit: this.data.unit_price,
            product_uom_qty: this.data.quantity,
            is_rental: true,
        };
    }

    /**
     * We let the regular process take place to allow the validation of the required fields
     * to happen.
     *
     * Then we can manually close the window, providing rental information to the caller.
     *
     * @override
     */
    async save(options = {}) {
        await super.save(options);
        this.model.action.doAction({type: 'ir.actions.act_window_close', infos: {
            rentalConfiguration: this._getRentalInfos()
        }});
    }
}

RentalConfiguratorRelationalModel.Record = RentalConfiguratorRecord;

registry.category("views").add("rental_configurator_form", {
    ...formView,
    Model: RentalConfiguratorRelationalModel,
});
