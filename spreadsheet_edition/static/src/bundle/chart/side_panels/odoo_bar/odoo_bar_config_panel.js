/** @odoo-module */

import { IrMenuSelector } from "@spreadsheet_edition/assets/components/ir_menu_selector/ir_menu_selector";
import { CommonOdooChartConfigPanel } from "../common/config_panel";

export class OdooBarChartConfigPanel extends CommonOdooChartConfigPanel {
    onUpdateStacked(ev) {
        this.props.updateChart({
            stacked: ev.target.checked,
        });
    }
}

OdooBarChartConfigPanel.template = "spreadsheet_edition.OdooBarChartConfigPanel";
OdooBarChartConfigPanel.components = { IrMenuSelector };
