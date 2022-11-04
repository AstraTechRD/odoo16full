odoo.define('web_mobile.mixins', function (require) {
"use strict";

const session = require('web.session');
const mobile = require('web_mobile.core');

/**
 * Mixin to setup lifecycle methods and allow to use 'backbutton' events sent
 * from the native application.
 *
 * @mixin
 * @name BackButtonEventMixin
 *
 */
var BackButtonEventMixin = {
    /**
     * Register event listener for 'backbutton' event when attached to the DOM
     */
    on_attach_callback: function () {
        mobile.backButtonManager.addListener(this, this._onBackButton);
    },
    /**
     * Unregister event listener for 'backbutton' event when detached from the DOM
     */
    on_detach_callback: function () {
        mobile.backButtonManager.removeListener(this, this._onBackButton);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev 'backbutton' type event
     */
    _onBackButton: function () {},
};

/**
 * Mixin to hook into the controller record's saving method and
 * trigger the update of the user's account details on the mobile app.
 *
 * @mixin
 * @name UpdateDeviceAccountControllerMixin
 *
 */
const UpdateDeviceAccountControllerMixin = {
    /**
     * @override
     */
    async save() {
        const changedFields = await this._super(...arguments);
        await session.updateAccountOnMobileDevice();
        return changedFields;
    },
};

/**
 * Trigger the update of the user's account details on the mobile app as soon as
 * the session is correctly initialized.
 */
session.is_bound.then(() => session.updateAccountOnMobileDevice());

return {
    BackButtonEventMixin: BackButtonEventMixin,
    UpdateDeviceAccountControllerMixin,
};

});

odoo.define('web_mobile.hooks', function (require) {
"use strict";

const { backButtonManager } = require('web_mobile.core');

const { onMounted, onPatched, onWillUnmount, useComponent } = owl;

/**
 * This hook provides support for executing code when the back button is pressed
 * on the mobile application of Odoo. This actually replaces the default back
 * button behavior so this feature should only be enabled when it is actually
 * useful.
 *
 * The feature is either enabled on mount or, using the `shouldEnable` function
 * argument as condition, when the component is patched. In both cases,
 * the feature is automatically disabled on unmount.
 *
 * @param {function} func the function to execute when the back button is
 *  pressed. The function is called with the custom event as param.
 * @param {function} [shouldEnable] the function to execute when the DOM is 
 *  patched to check if the backbutton should be enabled or disabled ; 
 *  if undefined will be enabled on mount and disabled on unmount.
 */
function useBackButton(func, shouldEnable) {
    const component = useComponent();
    let isEnabled = false;

    /**
     * Enables the func listener, overriding default back button behavior.
     */
    function enable() {
        backButtonManager.addListener(component, func);
        isEnabled = true;
    }

    /**
     * Disables the func listener, restoring the default back button behavior if
     * no other listeners are present.
     */
    function disable() {
        backButtonManager.removeListener(component);
        isEnabled = false;
    }

    onMounted(() => {
        if (shouldEnable && !shouldEnable()) {
            return;
        }
        enable();
    });

    onPatched(() => {
        if (!shouldEnable) {
            return;
        }
        const shouldBeEnabled = shouldEnable();
        if (shouldBeEnabled && !isEnabled) {
            enable();
        } else if (!shouldBeEnabled && isEnabled) {
            disable();
        }
    });

    onWillUnmount(() => {
        if (isEnabled) {
            disable();
        }
    });
}

return {
    useBackButton,
};
});
