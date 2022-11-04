odoo.define('web_studio.NewModel', function (require) {
"use strict";

const core = require('web.core');
const session = require('web.session');
const Widget = require('web.Widget');
const CommonMenuDialog = require('web_studio.CommonMenuDialog');

const _t = core._t;

const NewModelItem = Widget.extend({
    template: 'web_studio.NewModel',
    events: {
        'click .o_web_create_new_model': '_onClick',
    },

    /**
     * This new model widget provides the shortcut to create a
     * new model direct from the menubar.
     *
     * @constructor
     * @param {Widget} parent
     * @param {Integer} currentPrimaryMenu - for a current menu
     */
    init(parent, currentPrimaryMenu) {
        this._super(...arguments);
        this.current_primary_menu = currentPrimaryMenu;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Open a dialog to create new model.
     *
     * @private
     * @param {Event} event
     */
    _onClick(event) {
        event.preventDefault();
        new NewModelDialog(this, {
            parent_menu_id: this.current_primary_menu,
            on_saved(menu) {
                this.trigger_up('reload_menu_data');
                this.trigger_up('menu_clicked', {
                    openAction: true,
                    menu_id: this.current_primary_menu,
                    action_id: menu.action_id,
                    options: {viewType: 'form'},
                });
            },
        }).open();
    },

});

const NewModelDialog = CommonMenuDialog.extend({
    template: 'web_studio.NewModel.Dialog',

    /**
     * @constructor
     * @param {Widget} parent
     * @param {Object} params
     * @param {String} confirmlabel - label of the create model dialog
     */
    init(parent, params) {
        this.title = _t('Create a new Model');
        this.confirmLabel = _t('Create Model');
        this._super(...arguments);
    },

    /**
     * set buttons for the new model dialog
     *
     * @override
     */
    async willStart() {
        await this._super(...arguments);
        this.set_buttons([{
            text: _t("Configure Model"),
            classes: 'btn-primary confirm_button',
            click: this._onConfigureModel.bind(this),
        }, {
            text: _t("Cancel"),
            close: true
        }]);
    },

    /**
     * set focus on the model name input once dialog open
     *
     * @override
     */
    async start() {
        await this._super(...arguments);
        this.opened(() => {
            this.$modal.addClass('o_web_studio_new_model_modal');
            // focus on input
            this.el.querySelector('input[name="name"]').focus();
        });
    },

    /**
     * this method will create new menu and new model
     *
     * @private
     * @override
     * @param {String} menuName
     */
    _doSave(menuName) {
        this._super(...arguments);
        core.bus.trigger('clear_cache');
        return this._rpc({
            route: '/web_studio/create_new_menu',
            params: {
                menu_name: menuName,
                model_id: false,
                model_choice: 'new',
                model_options: this.model_options,
                parent_menu_id: this.parent_menu_id,
                context: session.user_context,
            },
        });
    },
});

return {
    NewModelItem: NewModelItem,
};

});
