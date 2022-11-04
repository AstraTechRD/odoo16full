/** @odoo-module  **/

import { _lt } from '@web/core/l10n/translation';
import { kanbanView } from '@web/views/kanban/kanban_view';
import { registry } from '@web/core/registry';
import { HelpdeskTeamKanbanController } from './helpdesk_team_kanban_controller';

export const HelpdeskTeamKanbanView = {
    ...kanbanView,
    Controller: HelpdeskTeamKanbanController,
    display_name: _lt('Dashboard'),
    icon: 'fa-dashboard',
    searchview_hidden: true,
};

registry.category('views').add('helpdesk_team_kanban_view', HelpdeskTeamKanbanView);
