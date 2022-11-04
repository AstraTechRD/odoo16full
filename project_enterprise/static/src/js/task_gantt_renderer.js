/** @odoo-module **/

import TaskGanttRow from './task_gantt_row';
import GanttRenderer from 'web_gantt.GanttRenderer';
import {getDateFormatForScale} from "./task_gantt_utils";
import core from 'web.core';

const QWeb = core.qweb;


export default GanttRenderer.extend({
    config: {
        GanttRow: TaskGanttRow,
    },
    events: Object.assign({ }, GanttRenderer.prototype.events || { }, {
        'mouseover .o_project_milestone_diamond': '_onMilestoneMouseEnter',
        'mouseleave .o_project_milestone_diamond': '_onMilestoneMouseLeave',
    }),

    //--------------------------------------------------------------------------
    // Life Cycle
    //--------------------------------------------------------------------------

    /**
     * @override
    */
    init() {
        this._super(...arguments);
        this.template_to_use = 'TaskGanttMilestonesView';
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     */
    _applySpecialColors(connector, masterRecord, slaveRecord) {
        if (masterRecord.display_warning_dependency_in_gantt && slaveRecord.display_warning_dependency_in_gantt) {
            this._super(...arguments);
        }
    },

    /**
     * @override
     * @private
     */
    _prepareViewInfo: function () {
        const viewInfo = this._super(...arguments);
        let dateFormat = getDateFormatForScale(this.SCALES[this.state.scale]);
        const slotsMilestonesDict = viewInfo.slots.reduce((accumulator, current) => {
            accumulator[current.format(dateFormat)] = {
                hasDeadLineExceeded: false,
                allReached: true,
                milestones: [],
            };
            return accumulator;
        }, { });
        this.state.milestones.forEach((milestone) => {
            const formattedDate = milestone.deadline.format(dateFormat);
            if (formattedDate in slotsMilestonesDict) {
                if (milestone.is_deadline_exceeded)
                    slotsMilestonesDict[formattedDate].hasDeadLineExceeded = true;
                if (!milestone.is_reached)
                    slotsMilestonesDict[formattedDate].allReached = false;
                slotsMilestonesDict[formattedDate].milestones.push(milestone);
            }
        });
        viewInfo.getSlotKey = (slot) => slot.format(dateFormat);
        viewInfo.slotsMilestonesDict = slotsMilestonesDict;
        viewInfo.slotMilestonesInfo = (slot) => {
            const slotKey = slot.format(dateFormat);
            return viewInfo.slotsMilestonesDict[slotKey];
        };
        return viewInfo;
    },
    /**
     *
     * @return {Promise<void>}
     * @private
     * @override
     */
    async _renderView() {
        await this._super(...arguments);
        this.el.classList.add('o_project_gantt');
    },
    /**
     * @private
     * @override
     */
    _shouldRenderRecordConnectors(record) {
        return record.allow_task_dependencies && this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    display_milestone_popover(data, targetElement) {
        const $milestone = $(targetElement);
        $milestone.popover({
            container: this.$el,
            delay: {show: this.POPOVER_DELAY},
            html: true,
            placement: 'auto',
            content: () => {
                return QWeb.render('gantt-milestone-popover', data);
            },
        });
        $milestone.popover("show");
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Handler for Milestones mouseenter event.
     * This is the moment when we render the popover template and create the popover.
     * This prevent using too much resources upfront.
     *
     * @param {OdooEvent} ev
     * @private
     */
    async _onMilestoneMouseEnter(ev) {
        ev.stopPropagation();
        this.trigger_up(
            'display_milestone_popover',
            {
                 popoverData: {
                    milestones: this.viewInfo.slotsMilestonesDict[ev.currentTarget.dataset.slotKey].milestones,
                    display_milestone_dates: this.viewInfo.state.scale === 'year'
                 },
                targetElement: ev.currentTarget,
            });
    },
    /**
     * Handler for Milestones mouseleave event.
     *
     *
     * @param {OdooEvent} ev
     * @private
     */
    async _onMilestoneMouseLeave(ev) {
        ev.stopPropagation();
        const $milestone = $(ev.currentTarget);
        $milestone.popover('dispose');
    },

});
