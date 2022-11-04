/** @odoo-module **/

import LineComponent from '@stock_barcode/components/line';
import { patch } from 'web.utils';


patch(LineComponent.prototype, 'stock_barcode_picking_batch', {

    get componentClasses() {
        return [
            this._super(),
            this.line.colorLine !== undefined ? 'o_colored_markup' : ''
        ].join(' ');
    }

});
