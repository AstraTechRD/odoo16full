/* global OdooDeviceUtility */
odoo.define('web_mobile.core', function () {
"use strict";

var available = typeof OdooDeviceUtility !== 'undefined';
var DeviceUtility;
var deferreds = {};
var methods = {};

if (available){
    DeviceUtility = OdooDeviceUtility;
    delete window.OdooDeviceUtility;
}

/**
 * Responsible for invoking native methods which called from JavaScript
 *
 * @param {String} name name of action want to perform in mobile
 * @param {Object} args extra arguments for mobile
 *
 * @returns Promise Object
 */
function native_invoke(name, args) {
    if(_.isUndefined(args)){
        args = {};
    }
    var id = _.uniqueId();
    args = JSON.stringify(args);
    DeviceUtility.execute(name, args, id);
    return new Promise(function (resolve, reject) {
        deferreds[id] = {
            successCallback: resolve,
            errorCallback: reject
        };
    });
}

/**
 * Manages deferred callback from initiate from native mobile
 *
 * @param {String} id callback id
 * @param {Object} result
 */
window.odoo.native_notify = function (id, result) {
    if (deferreds.hasOwnProperty(id)) {
        if (result.success) {
            deferreds[id].successCallback(result);
        } else {
            deferreds[id].errorCallback(result);
        }
    }
};

var plugins = available ? JSON.parse(DeviceUtility.list_plugins()) : [];
_.each(plugins, function (plugin) {
    methods[plugin.name] = function (args) {
        return native_invoke(plugin.action, args);
    };
});

/**
 * Use to notify an uri hash change on native devices (ios / android)
 */
if (methods.hashChange) {
    var currentHash;
    $(window).bind('hashchange', function (event) {
        var hash = event.getState();
        if (!_.isEqual(currentHash, hash)) {
            methods.hashChange(hash);
        }
        currentHash = hash;
    });
}

/**
 * Error related to the registration of a listener to the backbutton event
 */
class BackButtonListenerError extends Error {}

/**
 * By using the back button feature the default back button behavior from the
 * app is actually overridden so it is important to keep count to restore the
 * default when no custom listener are remaining.
 */
class BackButtonManager {

    constructor() {
        this._listeners = new Map();
        this._onGlobalBackButton = this._onGlobalBackButton.bind(this);
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Enables the func listener, overriding default back button behavior.
     *
     * @param {Widget|Component} listener
     * @param {function} func
     * @throws {BackButtonListenerError} if the listener has already been registered
     */
    addListener(listener, func) {
        if (!methods.overrideBackButton) {
            return;
        }
        if (this._listeners.has(listener)) {
            throw new BackButtonListenerError("This listener was already registered.");
        }
        this._listeners.set(listener, func);
        if (this._listeners.size === 1) {
            document.addEventListener('backbutton', this._onGlobalBackButton);
            methods.overrideBackButton({ enabled: true });
        }
    }
    /**
     * Disables the func listener, restoring the default back button behavior if
     * no other listeners are present.
     *
     * @param {Widget|Component} listener
     * @throws {BackButtonListenerError} if the listener has already been unregistered
     */
    removeListener(listener) {
        if (!methods.overrideBackButton) {
            return;
        }
        if (!this._listeners.has(listener)) {
            throw new BackButtonListenerError("This listener has already been unregistered.");
        }
        this._listeners.delete(listener);
        if (this._listeners.size === 0) {
            document.removeEventListener('backbutton', this._onGlobalBackButton);
            methods.overrideBackButton({ enabled: false });
        }
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _onGlobalBackButton() {
        const [listener, func] = [...this._listeners].pop();
        if (listener) {
            func.apply(listener, arguments);
        }
    }
}

const backButtonManager = new BackButtonManager();

return {
    BackButtonManager,
    BackButtonListenerError,
    backButtonManager,
    methods,
};

});
