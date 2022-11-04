/** @odoo-module */

import { unpatch } from "@web/core/utils/patch";
import { ListRenderer } from "@web/views/list/list_renderer";

unpatch(ListRenderer.prototype, "web_enterprise.ListRendererDesktop");
