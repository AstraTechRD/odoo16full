/** @odoo-module **/

import StandaloneM2OAvatarEmployee from '@hr/js/standalone_m2o_avatar_employee';

const EmployeeWithJobTitle = StandaloneM2OAvatarEmployee.extend({
    /**
     * Mute employee job title after rendering the widget.
     *
     * @override
     */
    start() {
        return this._super(...arguments).then(() => {
            this._muteJobTitle(this.$el.find(".o_m2o_avatar span:first"));
        });
    },
    /**
     * Mute the last content between parenthesis in Gantt title column
     *
     * @param {HTMLElement} span
     */
    _muteJobTitle(span) {
        const text = span.text();
        const jobTitleRegexp = /^(.*)(\(.*\))$/;
        const jobTitleMatch = text.match(jobTitleRegexp);
        if (jobTitleMatch) {
            span.empty();
            span.append(document.createTextNode(jobTitleMatch[1]));
            const textMuted = document.createElement('span');
            textMuted.className = 'text-muted';
            textMuted.appendChild(document.createTextNode(jobTitleMatch[2]));
            span.append(textMuted);
        }
    },
});

export default EmployeeWithJobTitle;
