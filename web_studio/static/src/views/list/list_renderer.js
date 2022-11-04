/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { ListRenderer } from "@web/views/list/list_renderer";
import { useService } from "@web/core/utils/hooks";

import "@web_enterprise/views/list/list_renderer_desktop";

export const patchListRendererStudio = {
    setup() {
        this._super(...arguments);
        this.studioService = useService("studio");
    },
    /**
     * This function opens the studio mode with current view
     *
     * @override
     */
    onSelectedAddCustomField() {
        this.studioService.open();
    },
};

patch(ListRenderer.prototype, "web_studio.ListRenderer", patchListRendererStudio);
