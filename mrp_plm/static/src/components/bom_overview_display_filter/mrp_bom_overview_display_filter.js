/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { BomOverviewDisplayFilter } from "@mrp/components/bom_overview_display_filter/mrp_bom_overview_display_filter";

patch(BomOverviewDisplayFilter.prototype, "mrp_plm", {
    setup() {
        this._super.apply();
        this.displayOptions.ecos = this.env._t('ECOs');
    },
});


patch(BomOverviewDisplayFilter, "mrp_plm", {
    props: {
        ...BomOverviewDisplayFilter.props,
        showOptions: { 
            ...BomOverviewDisplayFilter.showOptions,
            ecos: Boolean,
        },
    },
});
