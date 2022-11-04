/** @odoo-module */

import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";
import { CommonOdooChartConfigPanel } from "./common/config_panel";
import { OdooBarChartConfigPanel } from "./odoo_bar/odoo_bar_config_panel";
import { OdooLineChartConfigPanel } from "./odoo_line/odoo_line_config_panel";

const { chartSidePanelComponentRegistry } = spreadsheet.registries;
const { LineBarPieDesignPanel } = spreadsheet.components;

chartSidePanelComponentRegistry
    .add("odoo_line", {
        configuration: OdooLineChartConfigPanel,
        design: LineBarPieDesignPanel,
    })
    .add("odoo_bar", {
        configuration: OdooBarChartConfigPanel,
        design: LineBarPieDesignPanel,
    })
    .add("odoo_pie", {
        configuration: CommonOdooChartConfigPanel,
        design: LineBarPieDesignPanel,
    });
