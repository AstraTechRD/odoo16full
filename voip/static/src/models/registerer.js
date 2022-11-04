/** @odoo-module **/

import { registerModel } from "@mail/model/model_core";
import { attr, one } from "@mail/model/model_field";

import { sprintf } from "@web/core/utils/strings";
import { Markup } from "web.utils";

/**
 * Manages the registration to the Registrar (necessary to make the user
 * reachable).
 */
registerModel({
    name: "Registerer",
    lifecycleHooks: {
        _created() {
            const sipJsRegisterer = new window.SIP.Registerer(this.userAgent.__sipJsUserAgent, { expires: this.expirationInterval });
            sipJsRegisterer.stateChange.addListener((state) => this.update({ state }));
            this.update({
                state: sipJsRegisterer.state,
                __sipJsRegisterer: sipJsRegisterer,
            });
        },
        _willDelete() {
            this.__sipJsRegisterer.dispose();
        },
    },
    recordMethods: {
        /**
         * Sends the REGISTER request to the Registrar.
         */
        register() {
            this.__sipJsRegisterer.register({
                requestDelegate: {
                    onReject: (response) => this._onRegistrationRejected(response),
                },
            });
        },
        _onChangeState() {
            if (this.state === window.SIP.RegistererState.Registered) {
                this.messaging.messagingBus.trigger("sip_error_resolved");
            }
        },
        /**
         * Triggered when receiving a response with status code 4xx, 5xx, or 6xx
         * to the REGISTER request.
         *
         * @param {SIP.IncomingResponse} response The server final response to
         * the REGISTER request.
         */
        _onRegistrationRejected(response) {
            const errorMessage = sprintf(
                this.env._t("Registration rejected: %(statusCode)s %(reasonPhrase)s."),
                {
                    statusCode: response.message.statusCode,
                    reasonPhrase: response.message.reasonPhrase,
                },
            );
            const help = (() => {
                switch (response.message.statusCode) {
                    case 401: // Unauthorized
                        return this.env._t("The server failed to authenticate you. Please have an administrator verify that you are reaching the right server (PBX server IP in the General Settings) and that the credentials in your user preferences are correct.");
                    case 503: // Service Unavailable
                        return this.env._t("The error may come from the transport layer. Please have an administrator verify the websocket server URL in the General Settings. If the problem persists, this is probably an issue with the server.");
                    default:
                        return this.env._t("Please try again later. If the problem persists, you may want to ask an administrator to check the configuration.");
                }
            })();
            this.messaging.voip.triggerError(Markup`${errorMessage}</br></br>${help}`);
        },
    },
    fields: {
        /**
         * When sending a REGISTER request, an "expires" parameter with the
         * value of this field is added to the Contact header. It is used to
         * indicate how long we would like the registration to remain valid.
         * Note however that the definitive value is decided by the server based
         * on its own policy and may therefore differ.
         *
         * The library automatically renews the registration for the same
         * duration shortly before it expires.
         *
         * The value is expressed in seconds.
         */
        expirationInterval: attr({
            default: 3600,
            readonly: true,
        }),
        /**
         * Possible values:
         * - SIP.RegistererState.Initial
         * - SIP.RegistererState.Registered
         * - SIP.RegistererState.Unregistered
         * - SIP.RegistererState.Terminated
         */
        state: attr(),
        userAgent: one("UserAgent", {
            identifying: true,
            inverse: "registerer",
        }),
        /**
         * An instance of the Registerer class from the SIP.js library. It
         * shouldn't be used outside of this model; only the Registerer model is
         * responsible for interfacing with this object.
         */
        __sipJsRegisterer: attr(),
    },
    onChanges: [
        {
            dependencies: ["state"],
            methodName: "_onChangeState",
        },
    ],
});
