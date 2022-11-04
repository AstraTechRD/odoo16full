/** @odoo-module **/

import fieldUtils from 'web.field_utils';
import GanttRow from 'web_gantt.GanttRow';
import { getDateFormatForScale } from "./task_gantt_utils";
import StandaloneM2OAvatarUser from "./standalone_m2o_avatar_user";

export default GanttRow.extend({
    template: 'TaskGanttMilestonesView.Row',

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    init(parent, pillsInfo, viewInfo, options) {
        this._super(...arguments);
        const isGroupedByUser = pillsInfo.groupedByField === 'user_ids';
        this.showUserAvatar = isGroupedByUser && !!pillsInfo.resId;
    },

    /**
     * @override
     */
    async willStart() {
        const defs = [this._super(...arguments)];
        if (this.showUserAvatar) {
            defs.push(this._preloadAvatarWidget());
        }
        return Promise.all(defs);
    },

    /**
     * @override
     */
    start() {
        if (this.showUserAvatar) {
            this.avatarWidget.$el.appendTo(this.$('.o_gantt_row_user_avatar'));
        }
        return this._super(...arguments);
    },

    /**
     * @override
    */
    _prepareSlots: function () {
        this._super(...arguments);
        let dateFormat = getDateFormatForScale(this.SCALES[this.state.scale]);
        this.slots.forEach((slot) => {
            const slotKey = slot.start.format(dateFormat);
            slot.milestonesInfo = this.viewInfo.slotsMilestonesDict[slotKey];
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------
    _getUserID() {
        return this.resId;
    },

    /**
     * Initialize the avatar widget in virtual DOM.
     *
     * @private
     * @returns {Promise}
     */
    async _preloadAvatarWidget() {
        const user = [this._getUserID(), this.name];
        this.avatarWidget = new StandaloneM2OAvatarUser(this, user);
        return this.avatarWidget.appendTo(document.createDocumentFragment());
    },

    /**
     * Add allocated hours formatted to context
     *
     * @private
     * @override
     */
    _getPopoverContext: function () {
        const data = this._super.apply(this, arguments);
        data.allocatedHoursFormatted = fieldUtils.format.float_time(data.allocated_hours);
        return data;
    },
});
