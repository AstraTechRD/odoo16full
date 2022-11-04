/** @odoo-module */

const { Component } = owl;
import { _lt } from "@web/core/l10n/translation";

const FIELD_OFFSETS = [
    { value: 0, description: "" },
    { value: -1, description: _lt("Previous") },
    { value: -2, description: _lt("Before previous") },
    { value: 1, description: _lt("Next") },
    { value: 2, description: _lt("After next") },
];

export class FilterFieldOffset extends Component {
    setup() {
        this.fieldsOffsets = FIELD_OFFSETS;
    }
}
FilterFieldOffset.template = "spreadsheet_edition.FilterFieldOffset";
FilterFieldOffset.props = {
    onOffsetSelected: Function,
    selectedOffset: Number,
};
