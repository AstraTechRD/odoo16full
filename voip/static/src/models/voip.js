/** @odoo-module **/

import { registerModel } from "@mail/model/model_core";
import { attr, one } from "@mail/model/model_field";
import { clear } from "@mail/model/model_field_command";

/**
 * Models the global state of the VoIP module.
 */
registerModel({
    name: "Voip",
    recordMethods: {
        /**
         * Remove whitespaces, dashes, slashes and periods from a phone number.
         * @param {string} phoneNumber
         * @returns {string}
         */
        cleanPhoneNumber(phoneNumber) {
            // U+00AD is the "soft hyphen" character
            return phoneNumber.replace(/[\s-/.\u00AD]/g, "");
        },
        /**
         * Triggers an error that will be displayed in the softphone, and blocks
         * the UI by default.
         *
         * @param {string} message The error message to be displayed.
         * @param {Object} [options={}]
         * @param {boolean} [options.isNonBlocking=false] If true, the error
         * will not block the UI.
         */
        triggerError(message, { isNonBlocking = false } = {}) {
            this.messaging.messagingBus.trigger("sip_error", {
                isNonBlocking,
                message,
            });
        },
    },
    fields: {
        /**
         * Determines if `voip_secret` and `voip_username` settings are defined
         * for the current user.
         */
        areCredentialsSet: attr({
            compute() {
                if (!this.messaging.currentUser || !this.messaging.currentUser.res_users_settings_id) {
                    return clear();
                }
                return Boolean(
                    this.messaging.currentUser.res_users_settings_id.voip_username &&
                    this.messaging.currentUser.res_users_settings_id.voip_secret
                );
            },
            default: false,
        }),
        /**
         * With some providers, the authorization username (the one used to
         * register with the PBX server) differs from the username.
         */
        authorizationUsername: attr({
            compute() {
                if (!this.messaging.currentUser || !this.messaging.currentUser.res_users_settings_id) {
                    return clear();
                }
                return this.messaging.currentUser.res_users_settings_id.voip_username;
            },
            default: "",
        }),
        /**
         * Notes: this is a bit strange having to clean a string retrieved from
         * the server.
         */
        cleanedExternalDeviceNumber: attr({
            compute() {
                if (!this.messaging.currentUser || !this.messaging.currentUser.res_users_settings_id) {
                    return clear();
                }
                if (!this.messaging.currentUser.res_users_settings_id.external_device_number) {
                    return clear();
                }
                return this.cleanPhoneNumber(
                    this.messaging.currentUser.res_users_settings_id.external_device_number
                );
            },
            default: "",
        }),
        /**
         * Determines if `pbxAddress` and `webSocketUrl` are defined.
         */
        isServerConfigured: attr({
            compute() {
                return Boolean(this.pbxAddress && this.webSocketUrl);
            },
            default: false,
        }),
        /**
         * Either 'demo' or 'prod'. In demo mode, phone calls are simulated in
         * the interface but no RTC sessions are actually established.
         */
        mode: attr(),
        /**
         * The address of the PBX server.
         *
         * This is used as the hostname in SIP URIs.
         */
        pbxAddress: attr(),
        ringtoneRegistry: one("RingtoneRegistry", {
            default: {},
            inverse: "voip",
        }),
        userAgent: one("UserAgent", {
            inverse: "voip",
        }),
        /**
         * The WebSocket URL of the signaling server that will be used to
         * communicate SIP messages between Odoo and the PBX server.
         */
        webSocketUrl: attr(),
        /**
         * Determines if the `should_call_from_another_device` setting is set
         * and if an `external_device_number` has been provided.
         */
        willCallFromAnotherDevice: attr({
            compute() {
                if (!this.messaging.currentUser || !this.messaging.currentUser.res_users_settings_id) {
                    return clear();
                }
                return (
                    this.messaging.currentUser.res_users_settings_id.should_call_from_another_device &&
                    this.cleanedExternalDeviceNumber !== ""
                );
            },
            default: false,
        }),
    },
});
