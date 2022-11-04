/** @odoo-module */

import MockServer from 'web.MockServer';

MockServer.include({
    init() {
        this._super(...arguments);
        MockServer.currentMockServer = this;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     * @returns {Promise}
     */
    _performRpc: function (route) {
        if (route === '/web_studio/get_default_value') {
            return Promise.resolve({});
        }
        if (route === '/web_studio/activity_allowed') {
            return Promise.resolve(false);
        }
        return this._super.apply(this, arguments);
    },

    /**
     * Mocks method "_return_view" that generates the return value of a call
     * to edit_view. It's basically an object similar to the result of a call
     * to get_views. It is used in mockRPC functions that mock edit_view calls.
     *
     * @param {string} arch
     * @param {string} model
     * @private
     * @returns {Object}
     */
    _mockReturnView(arch, model) {
        const view = this.getView({ arch, model });
        const models = {};
        for (const modelName of view.models) {
            models[modelName] = this.fieldsGet(modelName);
        }
        return Promise.resolve({
            models,
            views: { [view.type]: view },
        });
    },
});
