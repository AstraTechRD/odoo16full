odoo.define('voip.dialingPanel', function (require) {
"use strict";

const core = require('web.core');

/**
 * @param {*} parent
 * @param {Object} action
 * @param {Object} [action.params={}]
 * @param {string} [action.params.number]
 */
function transferCall(parent, action) {
    const params = action.params || {};
    core.bus.trigger('transfer_call', params.number);
    return {
        type: 'ir.actions.act_window_close',
    };
}

core.action_registry.add("transfer_call", transferCall);

});
