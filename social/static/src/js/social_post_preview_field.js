/** @odoo-module **/

import { SocialPostFormatterMixin } from "./social_post_formatter_mixin";

import { HtmlField } from "@web_editor/js/backend/html_field";
import { patch } from '@web/core/utils/patch';
import { registry } from "@web/core/registry";
const { markup } = owl;

export class FieldPostPreview extends HtmlField {
    get markupValue() {
        const $html = $(this.props.value + '');
        $html.find('.o_social_preview_message').each((index, previewMessage) => {
            $(previewMessage).html(this._formatPost($(previewMessage).text().trim()));
        });

        return markup($html[0].outerHTML);
    }
}

FieldPostPreview.props = {
    ...FieldPostPreview.props,
    mediaType: { type: String, optional: true },
};

FieldPostPreview.extractProps = ({ attrs, field }) => {
    return {
        ...HtmlField.extractProps({ attrs, field }),
        mediaType: attrs.media_type || false,
    }
};


patch(FieldPostPreview.prototype, 'social_preview_formatter_mixin', SocialPostFormatterMixin);

registry.category("fields").add("social_post_preview", FieldPostPreview);
