/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PivotRenderer } from "@web/views/pivot/pivot_renderer";

const { useEffect, useRef } = owl;

patch(PivotRenderer.prototype, "web_enterprise.PivotRendererMobile", {
    setup() {
        this._super();
        this.root = useRef("root");
        if (this.env.isSmall) {
            useEffect(() => {
                const tooltipElems = this.root.el.querySelectorAll("*[data-tooltip]");
                for (const el of tooltipElems) {
                    el.removeAttribute("data-tooltip");
                    el.removeAttribute("data-tooltip-position");
                }
            });
        }
    },

    getPadding(cell) {
        if (this.env.isSmall) {
            return 5 + cell.indent * 5;
        }
        return this._super(...arguments);
    },
});
