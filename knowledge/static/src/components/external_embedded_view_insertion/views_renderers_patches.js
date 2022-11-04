/** @odoo-module */

import { _t } from "web.core";
import { CalendarRenderer } from "@web/views/calendar/calendar_renderer";
import { CohortRenderer } from "@web_cohort/cohort_renderer";
import { GraphRenderer } from "@web/views/graph/graph_renderer";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { ListRenderer } from "@web/views/list/list_renderer";
import { MapRenderer } from "@web_map/map_view/map_renderer";
import { patch } from "@web/core/utils/patch";
import { PivotRenderer } from "@web/views/pivot/pivot_renderer";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";
import {
    useBus,
    useOwnedDialogs,
    useService } from "@web/core/utils/hooks";
import { removeContextUserInfo } from "@spreadsheet_edition/assets/helpers";

/**
 * The following patch will add two new entries to the 'Favorites' dropdown menu
 * of the control panel namely: 'Insert view in article' and 'Insert link in article'.
 */
const EmbeddedViewRendererPatch = {
    setup() {
        this._super(...arguments);
        if (this.env.searchModel) {
            useBus(this.env.searchModel, 'insert-embedded-view', this._insertEmbeddedView.bind(this));
            useBus(this.env.searchModel, 'insert-view-link', this._insertViewLink.bind(this));
            this.orm = useService('orm');
            this.actionService = useService('action');
            this.addDialog = useOwnedDialogs();
        }
    },
    /**
     * @returns {Object}
     */
    _getViewContext: function () {
        if (this.env.searchModel) {
            return removeContextUserInfo(this.env.searchModel.context);
        }
        return {};
    },
    /**
     * @returns {Object}
     */
    _getViewState: function () {
        const state = {
            knowledge_embedded_view_framework: 'owl'
        };
        if (this.env.searchModel) {
            state.knowledge_search_model_state = JSON.stringify(this.env.searchModel.exportState());
        }
        return state;
    },
    _insertEmbeddedView: function () {
        const config = this.env.config;
        if (config.actionType !== 'ir.actions.act_window') {
            return;
        }
        this._openArticleSelector(async id => {
            const context = Object.assign({}, this._getViewContext(), this._getViewState());
            await this.orm.call('knowledge.article', 'append_embedded_view',
                [[id],
                config.actionId,
                config.viewType,
                config.getDisplayName(),
                context]
            );
            this.actionService.doAction('knowledge.ir_actions_server_knowledge_home_page', {
                additionalContext: {
                    res_id: id
                }
            });
        });
    },
    /**
     * Inserts a new link in the article redirecting the user to the current view.
     */
    _insertViewLink: function () {
        const config = this.env.config;
        if (config.actionType !== 'ir.actions.act_window') {
            return;
        }
        this._openArticleSelector(async id => {
            const context = Object.assign({}, this._getViewContext(), this._getViewState());
            await this.orm.call('knowledge.article', 'append_view_link',
                [[id],
                config.actionId,
                config.viewType,
                config.getDisplayName(),
                context]
            );
            this.actionService.doAction('knowledge.ir_actions_server_knowledge_home_page', {
                additionalContext: {
                    res_id: id
                }
            });
        });
    },
    /**
     * @param {Function} onSelectCallback
     */
    _openArticleSelector: function (onSelectCallback) {
        this.addDialog(SelectCreateDialog, {
            title: _t('Select an article'),
            noCreate: false,
            multiSelect: false,
            resModel: 'knowledge.article',
            context: {},
            domain: [
                ['user_has_write_access', '=', true]
            ],
            onSelected: resIds => {
                onSelectCallback(resIds[0]);
            },
            onCreateEdit: async () => {
                const articleId = await this.orm.call('knowledge.article', 'article_create', [], {
                    is_private: true
                });
                onSelectCallback(articleId);
            },
        });
    },
};

patch(CalendarRenderer.prototype, 'knowledge_calendar_embeddable', EmbeddedViewRendererPatch);
patch(CohortRenderer.prototype, 'knowledge_cohort_embeddable', EmbeddedViewRendererPatch);
patch(GraphRenderer.prototype, 'knowledge_graph_embeddable', EmbeddedViewRendererPatch);
patch(KanbanRenderer.prototype, 'knowledge_kanban_embeddable', EmbeddedViewRendererPatch);
patch(ListRenderer.prototype, 'knowledge_list_embeddable', EmbeddedViewRendererPatch);
patch(MapRenderer.prototype, 'knowledge_map_embeddable', EmbeddedViewRendererPatch);
patch(PivotRenderer.prototype, 'knowledge_pivot_embeddable', EmbeddedViewRendererPatch);

const supportedEmbeddedViews = new Set([
    'calendar',
    'cohort',
    'graph',
    'kanban',
    'list',
    'map',
    'pivot',
]);

export {
    supportedEmbeddedViews,
};
