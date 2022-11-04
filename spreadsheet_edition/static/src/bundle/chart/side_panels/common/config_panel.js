/** @odoo-module */

import { IrMenuSelector } from "@spreadsheet_edition/assets/components/ir_menu_selector/ir_menu_selector";

const { Component } = owl;

export class CommonOdooChartConfigPanel extends Component {
    get odooMenuId() {
        const menu = this.env.model.getters.getChartOdooMenu(this.props.figureId);
        return menu ? menu.id : undefined;
    }
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
    }
}

CommonOdooChartConfigPanel.template = "spreadsheet_edition.CommonOdooChartConfigPanel";
CommonOdooChartConfigPanel.components = { IrMenuSelector };
