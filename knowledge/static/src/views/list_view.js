/** @odoo-module */

import { registry } from '@web/core/registry';

import { listView } from '@web/views/list/list_view';
import { ListController } from '@web/views/list/list_controller';


export class KnowledgeArticleController extends ListController {
    setup() {
        super.setup();
        // Hide create button (creation cannot be deactivated to allow imports)
        this.activeActions['create'] = false;
    }

    /**
     * Add the "duplicate" action in the additional actions of the list view.
     * Place it as the second additional action for admin users.
     * @override
     */
    getActionMenuItems() {
        const actionMenuItems = super.getActionMenuItems();
        if (actionMenuItems && this.userService.isAdmin) {
            actionMenuItems.other.splice(1, 0, {
                description: this.env._t("Duplicate"),
                callback: async () => {
                    const selectedResIds = await this.getSelectedResIds();
                    if (selectedResIds.length === 1) {
                        await this.model.orm.call(this.props.resModel, "copy", [selectedResIds]);
                    } else {
                        await this.model.orm.call(this.props.resModel, "copy_batch", [selectedResIds]);
                    }
                    // Reloads the view to show the new duplicates
                    this.actionService.switchView("list");
                }
            });
        }
        return actionMenuItems;
    }
}

registry.category("views").add('knowledge_article_view_tree', {
    ...listView,
    Controller: KnowledgeArticleController,
});
