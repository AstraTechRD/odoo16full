/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Many2ManyTagsField } from "@web/views/fields/many2many_tags/many2many_tags_field";

import { HelpdeskSLATagsList } from "../helpdesk_sla_tags_list/helpdesk_sla_tags_list";


class HelpdeskSLAMany2ManyTags extends Many2ManyTagsField {
    getTagProps(record) {
        return { ...super.getTagProps(record), slaStatus: record.data.status };
    }
}

HelpdeskSLAMany2ManyTags.components = { ...Many2ManyTagsField.components, TagsList: HelpdeskSLATagsList };

HelpdeskSLAMany2ManyTags.fieldsToFetch = {
    ...Many2ManyTagsField.fieldsToFetch,
    status: { type: 'selection', selection: [] },
};

HelpdeskSLAMany2ManyTags.additionalClasses = [
    ...Many2ManyTagsField.additionalClasses || [],
    "o_field_many2many_tags",
];

registry.category("fields").add("helpdesk_sla_many2many_tags", HelpdeskSLAMany2ManyTags);
