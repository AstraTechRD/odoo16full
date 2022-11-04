/** @odoo-module */

import { isMobileOS } from "@web/core/browser/feature_detection";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { ListRenderer } from "@web/views/list/list_renderer";
import { PromoteStudioDialog } from "@web_enterprise/webclient/promote_studio_dialog/promote_studio_dialog";

export const patchListRendererDesktop = {
    setup() {
        this._super(...arguments);
        this.userService = useService("user");

        const { actionId, actionType } = this.env.config;
        const list = this.props.list;
        this.isStudioEditable =
            !isMobileOS() &&
            this.userService.isSystem &&
            actionId &&
            actionType === "ir.actions.act_window" &&
            list === list.model.root;
    },

    get displayOptionalFields() {
        return this.isStudioEditable || this.getOptionalFields.length;
    },

    /**
     * This function opens promote studio dialog
     *
     * @private
     */
    onSelectedAddCustomField() {
        this.env.services.dialog.add(PromoteStudioDialog, {});
    },
};

patch(ListRenderer.prototype, "web_enterprise.ListRendererDesktop", patchListRendererDesktop);
