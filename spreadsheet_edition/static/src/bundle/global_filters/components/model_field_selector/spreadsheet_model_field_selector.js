/** @odoo-module */

import { ModelFieldSelector } from "@web/core/model_field_selector/model_field_selector";
import { SpreadsheetModelFieldSelectorPopover } from "./spreadsheet_model_field_selector_popover";

export class SpreadsheetModelFieldSelector extends ModelFieldSelector {

    update(fieldNameChain, chain) {
        this.props.update(fieldNameChain.join("."), chain);
    }
}
SpreadsheetModelFieldSelector.components = {
    Popover: SpreadsheetModelFieldSelectorPopover,
}
