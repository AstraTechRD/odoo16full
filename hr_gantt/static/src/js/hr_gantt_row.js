odoo.define('hr_gantt.GanttRow', function (require) {
    'use strict';

    const GanttRow = require('web_gantt.GanttRow');
    const StandaloneM2OAvatarEmployee = require('@hr/js/standalone_m2o_avatar_employee')[Symbol.for("default")];

    const HrGanttRow = GanttRow.extend({
        template: 'HrGanttView.Row',

        /**
         * @override
         */
        init(parent, pillsInfo, viewInfo, options) {
            this._super(...arguments);
            const isGroupedByEmployee = pillsInfo.groupedByField === 'employee_id';
            this.showEmployeeAvatar = isGroupedByEmployee && !!pillsInfo.resId;
        },

        /**
         * @override
         */
        willStart() {
            const defs = [this._super(...arguments)];
            if (this.showEmployeeAvatar) {
                defs.push(this._preloadAvatarWidget());
            }
            return Promise.all(defs);
        },

        /**
         * @override
         */
        start() {
            if (this.showEmployeeAvatar) {
                this.avatarWidget.$el.appendTo(this.$('.o_gantt_row_employee_avatar'));
            }
            return this._super(...arguments);
        },

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------
        _getEmployeeID() {
            return this.resId;
        },

        /**
         * Initialize the avatar widget in virtual DOM.
         *
         * @private
         * @returns {Promise}
         */
        async _preloadAvatarWidget() {
            const employee = [this._getEmployeeID(), this.name];
            this.avatarWidget = new StandaloneM2OAvatarEmployee(this, employee);
            return this.avatarWidget.appendTo(document.createDocumentFragment());
        },
    });

    return HrGanttRow;
});
