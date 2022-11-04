/** @odoo-module **/

import { KanbanRenderer } from '@web/views/kanban/kanban_renderer';

import { StreamPostKanbanRecord } from './stream_post_kanban_record';

export class StreamPostKanbanRenderer extends KanbanRenderer {

    /**
     * Always display the no-content helper, even if there are groups.
     */
    get showNoContentHelper() {
        const { model } = this.props.list;
        return !model.hasData();
    }

}

StreamPostKanbanRenderer.template = 'social.KanbanRenderer';
StreamPostKanbanRenderer.components = {
    ...KanbanRenderer.components,
    KanbanRecord: StreamPostKanbanRecord,
};
