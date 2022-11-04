/** @odoo-module */

import { EmbeddedControllersPatch } from "@knowledge/views/embedded_controllers_patch";
import { ListController } from '@web/views/list/list_controller';
import { listView } from '@web/views/list/list_view';
import { patch } from "@web/core/utils/patch";
import { registry } from "@web/core/registry";

export class KnowledgeArticleItemsListController extends ListController {}

patch(KnowledgeArticleItemsListController.prototype, 'knowledge_embedded_list_controller', EmbeddedControllersPatch);

registry.category("views").add('knowledge_article_view_tree_embedded', {
    ...listView,
    Controller: KnowledgeArticleItemsListController
});
