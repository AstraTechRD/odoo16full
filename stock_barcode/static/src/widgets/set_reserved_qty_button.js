/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const { Component, onWillStart } = owl;

export class SetReservedQuantityButton extends Component {
    setup() {
        const user = useService('user');
        onWillStart(async () => {
            this.displayUOM = await user.hasGroup('uom.group_uom');
        });
    }

    get uom() {
        const [id, name] = this.props.record.data.product_uom_id || [];
        return { id, name };
    }

    _setQuantity (ev) {
        ev.stopPropagation();
        this.props.record.update({ [this.props.fieldToSet]: this.props.value });
    }
}

SetReservedQuantityButton.extractProps = ({ attrs }) => {
    if (attrs.field_to_set) {
        return { fieldToSet: attrs.field_to_set };
    }
};

SetReservedQuantityButton.template = 'stock_barcode.SetReservedQuantityButtonTemplate';
registry.category('fields').add('set_reserved_qty_button', SetReservedQuantityButton);
