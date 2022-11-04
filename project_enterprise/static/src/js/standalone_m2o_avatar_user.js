/** @odoo-module **/

import StandaloneFieldManagerMixin from 'web.StandaloneFieldManagerMixin';
import Widget from 'web.Widget';
import { Many2OneAvatarUser } from '@mail/js/m2x_avatar_user';

const StandaloneM2OAvatarUser = Widget.extend(StandaloneFieldManagerMixin, {
    className: 'o_standalone_avatar_user',

    /**
     * @override
     */
    init(parent, value) {
        this._super(...arguments);
        StandaloneFieldManagerMixin.init.call(this);
        this.value = value;
    },
    /**
     * @override
     */
    willStart() {
        return Promise.all([this._super(...arguments), this._makeAvatarWidget()]);
    },
    /**
     * @override
     */
    start() {
        this.avatarWidget.$el.appendTo(this.$el);
        return this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Create a record, and initialize and start the avatar widget.
     *
     * @private
     * @returns {Promise}
     */
    async _makeAvatarWidget() {
        const modelName = 'res.users';
        const fieldName = 'user_ids';
        const recordId = await this.model.makeRecord(modelName, [{
            name: fieldName,
            relation: modelName,
            type: 'many2one',
            value: this.value,
        }]);
        const state = this.model.get(recordId);
        this.avatarWidget = new Many2OneAvatarUser(this, fieldName, state);
        this._registerWidget(recordId, fieldName, this.avatarWidget);
        return this.avatarWidget.appendTo(document.createDocumentFragment());
    },
});

export default StandaloneM2OAvatarUser;
