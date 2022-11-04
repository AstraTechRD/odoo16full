/** @odoo-module **/

import { bus } from 'web.core';
import LineComponent from './line';

export default class PackageLineComponent extends LineComponent {
    get componentClasses() {
        return [
            this.qtyDone == 1 ? 'o_line_completed' : 'o_line_not_completed',
            this.isSelected ? 'o_selected o_highlight' : ''
        ].join(' ');
    }

    get isSelected() {
        return this.line.package_id.id === this.env.model.lastScanned.packageId;
    }

    get qtyDemand() {
        return this.props.line.reservedPackage ? 1 : false;
    }

    get qtyDone() {
        const reservedQuantity = this.line.lines.reduce((r, l) => r + l.reserved_uom_qty, 0);
        const doneQuantity = this.line.lines.reduce((r, l) => r + l.qty_done, 0);
        if (reservedQuantity > 0) {
            return doneQuantity / reservedQuantity;
        }
        return doneQuantity >= 0 ? 1 : 0;
    }

    openPackage() {
        bus.trigger('open-package', this.line.package_id.id);
    }

    select(ev) {
        ev.stopPropagation();
        this.env.model.selectPackageLine(this.line);
        this.env.model.trigger('update');
    }
}
PackageLineComponent.template = 'stock_barcode.PackageLineComponent';
