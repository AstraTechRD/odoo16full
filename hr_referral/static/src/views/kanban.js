/** @odoo-module */

import { registry } from '@web/core/registry';
import { useService } from "@web/core/utils/hooks";

import { kanbanView } from '@web/views/kanban/kanban_view';
import { KanbanRenderer } from '@web/views/kanban/kanban_renderer';

import session from 'web.session';

const { useState, onWillStart } = owl;

export class ReferralKanbanRenderer extends KanbanRenderer {
    setup() {
        super.setup();

        this.orm = useService('orm');
        this.companyId = session.user_context.allowed_company_ids[0];
        this.state = useState({
            showGrass: true
        });

        onWillStart(async () => {
            const referralData = await this.orm.call('hr.applicant', 'retrieve_referral_data');
            this.state.showGrass = referralData.show_grass || true;
        });
    }
}
ReferralKanbanRenderer.template = 'hr_referral.KanbanRenderer';

registry.category('views').add('referral_kanban', {
    ...kanbanView,
    Renderer: ReferralKanbanRenderer,
});
