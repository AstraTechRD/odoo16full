/** @odoo-module */

import { useService } from '@web/core/utils/hooks';

const EmbeddedControllersPatch = {
    /**
     * @override
     */
    setup() {
        this._super(...arguments);
        this.orm = useService('orm');
    },
    /**
     * Action when clicking on the Create button for list and kanban embedded
     * views (for knowledge.article).
     * Create an article item and redirect to its form view
     *
     * @override
     */
    async createRecord() {
        const articleId = await this.orm.call('knowledge.article', 'article_create', [], {
            is_article_item: true,
            is_private: false,
            parent_id: this.props.context.active_id || false
        });
        this.actionService.doAction(
            await this.orm.call('knowledge.article', 'action_home_page', [articleId]),
            {}
        );
    },
};

export {
    EmbeddedControllersPatch
};
