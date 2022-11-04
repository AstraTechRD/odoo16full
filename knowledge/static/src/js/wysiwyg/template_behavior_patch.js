/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { setCursorStart } from "@web_editor/js/editor/odoo-editor/src/OdooEditor";
import { TemplateBehavior } from "@knowledge/components/behaviors/template_behavior/template_behavior";

const TemplateBehaviorPatch = {
    /**
     * Set the cursor of the user inside the template block when the user types
     * the `/template` command.
     */
    setCursor() {
        setCursorStart(this.props.anchor.querySelector('[data-prop-name="content"] > p'));
    },
};

patch(TemplateBehavior.prototype, 'template_behavior_wysiwyg', TemplateBehaviorPatch);
