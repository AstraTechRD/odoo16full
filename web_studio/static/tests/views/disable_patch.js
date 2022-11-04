/** @odoo-module */

import { unpatch } from "@web/core/utils/patch";
import { ListRenderer } from "@web/views/list/list_renderer";

import "@web_studio/views/list/list_renderer";

unpatch(ListRenderer.prototype, "web_studio.ListRenderer");
