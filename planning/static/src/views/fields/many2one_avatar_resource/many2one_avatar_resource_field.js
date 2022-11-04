/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Many2OneAvatarField } from "@web/views/fields/many2one_avatar/many2one_avatar_field";

export class Many2OneAvatarResourceField extends Many2OneAvatarField {}
Many2OneAvatarResourceField.template = "planning.Many2OneAvatarResourceField";
Many2OneAvatarResourceField.fieldDependencies = {
    resource_type: { type: "selection" },
};
Many2OneAvatarResourceField.additionalClasses = ["o_field_many2one_avatar"];

registry.category("fields").add("many2one_avatar_resource", Many2OneAvatarResourceField);
