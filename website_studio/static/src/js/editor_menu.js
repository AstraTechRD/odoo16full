/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";

registry
    .category("web_studio.editor_tabs")
    .add('website', { name: _lt("Website"), action: "action_web_studio_form" });
