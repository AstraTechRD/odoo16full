/** @odoo-module **/

import GanttController from 'web_gantt.GanttController';
import { _t } from 'web.core';


export default GanttController.extend({
    custom_events: Object.assign(
        { },
        GanttController.prototype.custom_events,
        {
            display_milestone_popover: '_onDisplayMilestonePopover',
        }),

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @override
     * @param {OdooEvent} ev
     * @private
     */
    _onDisplayMilestonePopover: function (ev) {
        ev.stopPropagation();
        Object.assign(
            ev.data.popoverData,
            {
                display_project_name: !!this.context.search_default_my_tasks,
            });
        this.renderer.display_milestone_popover(ev.data.popoverData, ev.data.targetElement);
    },

    /**
     * @private
     * @override
     * @param {Object} context
     */
    _openPlanDialog(context) {
        this.openPlanDialogCallback = (res) => {
            if (res) {
                if (res.action) {
                    this.do_action(res.action);
                }
                if (res.warnings) {
                    for (const warning of res.warnings) {
                        this.displayNotification({
                            title: _t('Warning'),
                            message: warning,
                            sticky: true,
                        });
                    }
                }
            }
        };
        context.smart_task_scheduling = true;
        this._super(context);
    },

    //--------------------------------------------------------------------------
    // Utils
    //--------------------------------------------------------------------------
    /**
     * In the case of special Many2many Fields, like personal_stage_type_ids in project.task
     * model, we don't want to write the many2many field but use the inverse method of the
     * linked Many2one field, in this case the personal_stage_type_id, to create or update the
     * record - here set the stage_id - in the personal_stage_type_ids.
     *
     * This is mandatory since the python ORM doesn't support the creation of
     * a personnal stage from scratch. If this method is not overriden, then an entry
     * will be inserted in the project_task_user_rel.
     * One for the faked Many2many user_ids field (1), and a second one for the other faked
     * Many2many personal_stage_type_ids field (2).
     *
     * While the first one meets the constraint on the project_task_user_rel, the second one
     * fails because it specifies no user_id; It tries to insert (task_id, stage_id) into the
     * relation.
     *
     * If we don't remove those key from the context, the ORM will face two problems :
     * - It will try to insert 2 entries in the project_task_user_rel
     * - It will try to insert an incorrect entry in the project_task_user_rel
     *
     * @private
     * @override
     */
    _getDialogContext: function () {
        const context = this._super.apply(this, arguments);
        for (let mapping of this.model.mapMany2manyFields) {
            if (mapping.many2many_field in context) {
                context[mapping.many2one_field] = context[mapping.many2many_field][0];
                delete context[mapping.many2many_field];
            }
        }
        if ('user_ids' in context && !context['user_ids']) {
            delete context['user_ids'];
        }
        return context;
    },
});
