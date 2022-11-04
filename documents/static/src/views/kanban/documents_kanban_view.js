/** @odoo-module **/

import { registry } from "@web/core/registry";

import { kanbanView } from "@web/views/kanban/kanban_view";
import { DocumentsKanbanController } from "./documents_kanban_controller";
import { DocumentsKanbanModel } from "./documents_kanban_model";
import { DocumentsKanbanRenderer } from "./documents_kanban_renderer";
import { DocumentsSearchModel } from "../search/documents_search_model";
import { DocumentsSearchPanel } from "../search/documents_search_panel";

import { device } from "web.config";

const buttonTemplate = device.isMobile
    ? "documents.DocumentsViews.ControlPanelMobile"
    : "documents.DocumentsViews.ControlPanel";

export const DocumentsKanbanView = Object.assign({}, kanbanView, {
    SearchModel: DocumentsSearchModel,
    SearchPanel: DocumentsSearchPanel,
    Controller: DocumentsKanbanController,
    Model: DocumentsKanbanModel,
    Renderer: DocumentsKanbanRenderer,
    searchMenuTypes: ["filter", "favorite"],
    buttonTemplate: buttonTemplate,
});

registry.category("views").add("documents_kanban", DocumentsKanbanView);
