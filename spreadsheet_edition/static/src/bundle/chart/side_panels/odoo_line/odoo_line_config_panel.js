/** @odoo-module */

import { IrMenuSelector } from "@spreadsheet_edition/assets/components/ir_menu_selector/ir_menu_selector";
import { CommonOdooChartConfigPanel } from "../common/config_panel";

export class OdooLineChartConfigPanel extends CommonOdooChartConfigPanel {
    onUpdateStacked(ev) {
        this.props.updateChart({
            stacked: ev.target.checked,
        });
    }
}

OdooLineChartConfigPanel.template = "spreadsheet_edition.OdooLineChartConfigPanel";
OdooLineChartConfigPanel.components = { IrMenuSelector };
