/** @odoo-module */

import { unpatch } from "@web/core/utils/patch";
import { GraphController } from "@web/views/graph/graph_controller";

unpatch(GraphController.prototype, "graph_spreadsheet");
