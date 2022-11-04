/** @odoo-module */

import { ModelFieldSelectorPopover } from "@web/core/model_field_selector/model_field_selector_popover";

export class SpreadsheetModelFieldSelectorPopover extends ModelFieldSelectorPopover {
    async update() {
        const fieldNameChain = this.fieldNameChain;
        this.fullFieldName = fieldNameChain.join(".");
        await this.props.update(fieldNameChain, [...this.chain]);
        await this.loadFields();
        this.render();
    }
}
