/** @odoo-module */

import { patch } from '@web/core/utils/patch';
import { ProjectRightSidePanel } from '@project/components/project_right_side_panel/project_right_side_panel';

patch(ProjectRightSidePanel.prototype, '@project_account_budget/components/project_right_side_panel/project_right_side_panel', {
    async loadBudgets() {
        const budgets = await this.orm.call(
            'project.project',
            'get_budget_items',
            [[this.projectId]],
            { context: this.context },
        );
        this.state.data.budget_items = budgets;
        return budgets;
    },

    addBudget() {
        const context = {
            ...this.context,
            project_update: true,
            default_project_id: this.projectId,
        };
        this.openFormViewDialog({
            context,
            title: this.env._t('New Budget'),
            resModel: 'crossovered.budget',
            onRecordSaved: async () => {
                await this.loadBudgets();
            },
            viewId: this.state.data.budget_items.form_view_id,
        });
    }
});
