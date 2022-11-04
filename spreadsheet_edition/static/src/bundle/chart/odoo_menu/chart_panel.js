/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";
import { IrMenuSelector } from "@spreadsheet_edition/assets/components/ir_menu_selector/ir_menu_selector";

const { LineBarPieConfigPanel, ScorecardChartConfigPanel, GaugeChartConfigPanel } =
    spreadsheet.components;

/**
 * Patch the chart configuration panel to add an input to
 * link the chart to an Odoo menu.
 */
function patchChartPanelWithMenu(PanelComponent, patchName) {
    patch(PanelComponent.prototype, patchName, {
        get odooMenuId() {
            const menu = this.env.model.getters.getChartOdooMenu(this.props.figureId);
            return menu ? menu.id : undefined;
        },
        /**
         * @param {number | undefined} odooMenuId
         */
        updateOdooLink(odooMenuId) {
            if (!odooMenuId) {
                this.env.model.dispatch("LINK_ODOO_MENU_TO_CHART", {
                    chartId: this.props.figureId,
                    odooMenuId: undefined,
                });
                return;
            }
            const menu = this.env.model.getters.getIrMenu(odooMenuId);
            this.env.model.dispatch("LINK_ODOO_MENU_TO_CHART", {
                chartId: this.props.figureId,
                odooMenuId: menu.xmlid || menu.id,
            });
        },
    });
    PanelComponent.components = {
        ...PanelComponent.components,
        IrMenuSelector,
    };
}
patchChartPanelWithMenu(LineBarPieConfigPanel, "document_spreadsheet.LineBarPieConfigPanel");
patchChartPanelWithMenu(GaugeChartConfigPanel, "document_spreadsheet.GaugeChartConfigPanel");
patchChartPanelWithMenu(
    ScorecardChartConfigPanel,
    "document_spreadsheet.ScorecardChartConfigPanel"
);
