/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { BomOverviewComponent } from "@mrp/components/bom_overview/mrp_bom_overview";

patch(BomOverviewComponent.prototype, "mrp_plm", {
    setup() {
        this._super.apply();
        this.state.showOptions.ecos = false;
    },

    getReportName(printAll) {
        return this._super.apply(this, arguments) + "&show_ecos=" + this.state.showOptions.ecos;
    }
});
