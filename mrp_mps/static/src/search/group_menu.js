/** @odoo-module **/

import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

const { Component } = owl;

export class GroupMenu extends Component {
    get items() {
        return this.props.items;
    }

    _toggle_group(group) {
        const value = {};
        value[group] = !this.props.items[group];
        this.env.model._saveCompanySettings(value);
    }

}

GroupMenu.template = "mrp_mps.GroupMenu";
GroupMenu.components = { Dropdown, DropdownItem };
