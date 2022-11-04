/** @odoo-module **/

import { registry } from "@web/core/registry";
import { TagsList } from "@web/views/fields/many2many_tags/tags_list";
import { KanbanMany2ManyTagsField } from "@web/views/fields/many2many_tags/kanban_many2many_tags_field";
import { Many2ManyTagsField } from "@web/views/fields/many2many_tags/many2many_tags_field";

// Add support for hexadecimal colors
export class DocumentsTagsList extends TagsList {}
DocumentsTagsList.template = "documents.DocumentsTagsList";

const getDocumentTags = (component, superTags) => {
    if (!component.env.searchModel.getTags) {
        return superTags;
    }
    const searchModelTags = component.env.searchModel.getTags();
    if (!searchModelTags.length) {
        return superTags;
    }
    const searchModelTagByRecordId = searchModelTags.reduce((res, rec) => {
        res[rec.id] = rec;
        return res;
    }, {});
    const recordByTagId = component.props.value.records.reduce((res, rec) => {
        res[rec.id] = rec;
        return res;
    }, {});
    return superTags
        .filter((tag) => searchModelTagByRecordId[recordByTagId[tag.id].resId])
        .map((tag) => {
            const record = recordByTagId[tag.id];
            const searchModelTag = searchModelTagByRecordId[record.resId];
            tag.group_hex_color = searchModelTag.group_hex_color;
            tag.text = searchModelTag.display_name;
            return tag;
        });
};

// This widget only displays the tags that are currently in the search panel
export class DocumentsKanbanMany2ManyTagsField extends KanbanMany2ManyTagsField {
    get tags() {
        return getDocumentTags(this, super.tags);
    }
}
DocumentsKanbanMany2ManyTagsField.components = {
    ...DocumentsKanbanMany2ManyTagsField.components,
    TagsList: DocumentsTagsList,
};
registry.category("fields").add("kanban.documents_many2many_tags", DocumentsKanbanMany2ManyTagsField);

export class DocumentsMany2ManyTagsField extends Many2ManyTagsField {
    get tags() {
        return getDocumentTags(this, super.tags);
    }
}
DocumentsMany2ManyTagsField.components = {
    ...DocumentsMany2ManyTagsField.components,
    TagsList: DocumentsTagsList,
};
registry.category("fields").add("documents_many2many_tags", DocumentsMany2ManyTagsField);
