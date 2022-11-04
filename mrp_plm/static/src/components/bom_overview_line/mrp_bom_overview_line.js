/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { BomOverviewLine } from "@mrp/components/bom_overview_line/mrp_bom_overview_line";

patch(BomOverviewLine.prototype, "mrp_plm", {
    //---- Handlers ----

    async goToEco() {
        return this.actionService.doAction({
            name: this.env._t("ECOs"),
            type: "ir.actions.act_window",
            res_model: "mrp.eco",
            domain: [["product_tmpl_id.product_variant_ids", "in", [this.data.product_id]]],
            views: [[false, "kanban"], [false, "list"], [false, "form"]],
            target: "current",
        });
    }
});

patch(BomOverviewLine, "mrp_plm", {
    props: {
        ...BomOverviewLine.props,
        showOptions: { 
            ...BomOverviewLine.showOptions,
            ecos: Boolean,
        },
    },
});
