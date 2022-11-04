odoo.define('voip.UserAgent', function (require) {
"use strict";

const Class = require('web.Class');
const concurrency = require('web.concurrency');
const core = require('web.core');
const { escape, sprintf } = require('@web/core/utils/strings');
const mixins = require('web.mixins');
const mobile = require('web_mobile.core');
const ServicesMixin = require('web.ServicesMixin');

const _t = core._t;

const CALL_STATE = {
    NO_CALL: 0,
    RINGING_CALL: 1,
    ONGOING_CALL: 2,
    CANCELING_CALL: 3,
    REJECTING_CALL: 4,
};

const UserAgent = Class.extend(mixins.EventDispatcherMixin, ServicesMixin, {
    /**
     * @constructor
     */
    init(parent) {
        var self = this;
        mixins.EventDispatcherMixin.init.call(this);
        this.setParent(parent);
        this._updateCallState(CALL_STATE.NO_CALL);
        /**
         * The phone number of the current external party.
         */
        this._currentNumber = undefined;
        /**
         * The partner id and the phone number of the current external party.
         */
        this._currentCallParams = false;
        /**
         * The session created from an inbound invitation.
         */
        this._currentInviteSession = false;
        /**
         * Determines the direction of the ongoing call (either outgoing or
         * incoming).
         */
        this._isOutgoing = false;
        /**
         * Represents the real-time communication session between two user
         * agents, managed according to the SIP protocol.
         */
        this._sipSession = undefined;
        /**
         * The id of the setTimeout used in demo mode to simulate the waiting
         * time before the call is picked up.
         */
        this._timerAcceptedTimeout = undefined;

        owl.Component.env.services.messaging.get().then((messaging) => {
            this._messaging = messaging;
            this.voip = messaging.voip;
            this._initUserAgent();
        });

        window.onbeforeunload = function (event) {
            if (self._callState !== CALL_STATE.NO_CALL) {
                return _t("Are you sure that you want to close this website? There's a call ongoing.");
            }
        };
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Accept an incoming Call
     */
    acceptIncomingCall() {
        this._answerCall();
    },
    /**
     * @param useVoIPChoice
     */
    async updateCallPreference(useVoIPChoice) {
        await this._messaging.rpc(
            {
                model: 'res.users.settings',
                method: 'set_res_users_settings',
                args: [[this._messaging.currentUser.res_users_settings_id.id], {
                    how_to_call_on_mobile: useVoIPChoice,
                }],
            },
            { shadow: true },
        );
    },
    /**
     * Hangs up the current call.
     */
    hangup() {
        if (this._callState === CALL_STATE.ONGOING_CALL) {
            this._terminateSession();
        }
        if (this._callState === CALL_STATE.RINGING_CALL) {
            this._cancelEstablishingSession();
        }
    },
    /**
     * Instantiates a new sip call.
     *
     * @param {string} number
     */
    makeCall(number) {
        if (this.voip.mode === 'demo') {
            this.voip.ringtoneRegistry.ringbackTone.play({ loop: true });
            this._timerAcceptedTimeout = this._demoTimeout(() => this._onOutgoingInvitationAccepted());
            this._isOutgoing = true;
            this._updateCallState(CALL_STATE.RINGING_CALL);
            return;
        }
        this._makeCall(number);
    },
    /**
     * Mutes the current call
     */
    muteCall() {
        if (this.voip.mode === 'demo') {
            return;
        }
        if (this._callState !== CALL_STATE.ONGOING_CALL) {
            return;
        }
        this._setMute(true);
    },
    /**
     * Reject an incoming Call
     */
    rejectIncomingCall() {
        this._messaging.messagingBus.trigger('sip_rejected', this._currentCallParams);
        this.voip.ringtoneRegistry.incomingCallRingtone.stop();
        this._sipSession = false;
        this._updateCallState(CALL_STATE.NO_CALL);
        if (this._currentInviteSession) {
            this._currentInviteSession.reject({ statusCode: 603 });
        }
        if (this._notification) {
            this._notification.removeEventListener('close', this._rejectInvite, this._currentInviteSession);
            this._notification.close();
            this._notification = undefined;
        }
    },
    /**
     * Sends dtmf, when there is a click on keypad number.
     *
     * @param {string} number number clicked
     */
    sendDtmf(number) {
        if (this.voip.mode === 'demo') {
            return;
        }
        if (this._callState !== CALL_STATE.ONGOING_CALL) {
            return;
        }
        this._sipSession.sessionDescriptionHandler.sendDtmf(number);
    },
    /**
     * Transfers the call to the given number.
     *
     * @param {string} number
     */
    transfer(number) {
        if (this.voip.mode === 'demo') {
            this._updateCallState(CALL_STATE.NO_CALL);
            this._messaging.messagingBus.trigger('sip_bye');
            return;
        }
        if (this._callState !== CALL_STATE.ONGOING_CALL) {
            return;
        }
        const transferTarget = window.SIP.UserAgent.makeURI(`sip:${number}@${this.voip.pbxAddress}`);
        this._sipSession.refer(transferTarget, {
            requestDelegate: {
                onAccept: (response) => this._onReferAccepted(response),
            },
        });
    },
    unmuteCall() {
        if (this.voip.mode === 'demo') {
            return;
        }
        if (this._callState !== CALL_STATE.ONGOING_CALL) {
            return;
        }
        this._setMute(false);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Answer to a INVITE message and accept the call.
     *
     * @private
     */
    _answerCall() {
        const inviteSession = this._currentInviteSession;

        if (this.voip.mode === 'demo') {
            this._updateCallState(CALL_STATE.ONGOING_CALL);
            this._messaging.messagingBus.trigger('sip_incoming_call', this._currentCallParams);
            return;
        }
        if (!inviteSession) {
            return;
        }

        this.voip.ringtoneRegistry.incomingCallRingtone.stop();
        const callOptions = {
            sessionDescriptionHandlerOptions: {
                constraints: { audio: true, video: false },
            },
        };
        inviteSession.accept(callOptions);
        this._isOutgoing = false;
        this._sipSession = inviteSession;
        this.voip.triggerError(_t("Please accept the use of the microphone."));
    },
    /**
     * Exits the `ringing` state. In production mode, sends a CANCEL request to
     * cancel the session in progress.
     *
     * @private
     */
    _cancelEstablishingSession() {
        this.voip.ringtoneRegistry.stopAll();
        this._updateCallState(CALL_STATE.NO_CALL);
        this._messaging.messagingBus.trigger('sip_cancel_outgoing');
        if (this._sipSession) {
            this._sipSession.cancel();
            this._sipSession = false;
        }
        if (this.voip.mode === 'demo') {
            clearTimeout(this._timerAcceptedTimeout);
        }
    },
    /**
     * Clean the audio media stream after a call.
     *
     * @private
     */
    _cleanRemoteAudio() {
        this.$remoteAudio.srcObject = null;
        this.$remoteAudio.pause();
    },
    /**
     * Configure the remote audio, the ringtones
     *
     * @private
     */
    _configureDomElements() {
        this.$remoteAudio = document.createElement('audio');
        this.$remoteAudio.autoplay = true;
        $('html').append(this.$remoteAudio);
    },
    /**
     * Configure the audio media stream, at the begining of a call.
     *
     * @private
     */
    _configureRemoteAudio() {
        const remoteStream = new MediaStream();
        for (const receiver of this._sipSession.sessionDescriptionHandler.peerConnection.getReceivers()) {
            if (receiver.track) {
                remoteStream.addTrack(receiver.track);
                // According to the SIP.js documentation, this is needed by Safari to work.
                this.$remoteAudio.load();
            }
        }
        this.$remoteAudio.srcObject = remoteStream;
        if (!this._messaging.isInQUnitTest) {
            this.$remoteAudio.play().catch(() => {});
        }
    },
    /**
     * Instantiates a new user agent using the current configuration.
     *
     * @private
     * @return {SIP.UserAgent|false} Returns `false` if some mandatory
     * configurations are missing.
     */
    _createUserAgent() {
        if (!this.voip.isServerConfigured) {
            this.voip.triggerError(_t("PBX or Websocket address is missing. Please check your settings."));
            return false;
        }
        if (!this.voip.areCredentialsSet) {
            this.voip.triggerError(_t("Your credentials are not correctly set. Please contact your administrator."));
            return false;
        }
        return new window.SIP.UserAgent(this._getUaConfig());
    },
    /**
     * @private
     * @param {function} func
     */
    _demoTimeout(func) {
        return setTimeout(func, 3000);
    },
    /**
     * Provides the function that will be used by the SIP.js library to create
     * the media source that will serve as the local media stream (i.e. the
     * recording of the user's microphone).
     *
     * @returns {SIP.MediaStreamFactory}
     */
    _getMediaStreamFactory() {
        return (constraints, sessionDescriptionHandler) => {
            const mediaRequest = navigator.mediaDevices.getUserMedia(constraints);
            mediaRequest.then(
                (stream) => this._onGetUserMediaSuccess(stream),
                (error) => this._onGetUserMediaFailure(error)
            );
            return mediaRequest;
        };
    },
    /**
     * Provides the handlers to be called by the SIP.js library when receiving
     * SIP requests (BYE, INFO, ACK, REFER…).
     *
     * @returns {SIP.SessionDelegate}
     */
    _getSessionDelegate() {
        return {
            onBye: (bye) => this._onBye(bye),
        };
    },
    /**
     * Returns the UA configuration required.
     *
     * @private
     * @return {Object} the ua configuration parameters
     */
    _getUaConfig() {
        const isDebug = owl.Component.env.isDebug() !== '';
        return {
            authorizationPassword: this._messaging.currentUser.res_users_settings_id.voip_secret,
            authorizationUsername: this.voip.authorizationUsername,
            delegate: {
                onDisconnect: (error) => this._onDisconnect(error),
                onInvite: (inviteSession) => this._onInvite(inviteSession),
            },
            hackIpInContact: true,
            logBuiltinEnabled: isDebug,
            logLevel: isDebug ? 'debug' : 'error',
            sessionDescriptionHandlerFactory: window.SIP.Web.defaultSessionDescriptionHandlerFactory(this._getMediaStreamFactory()),
            sessionDescriptionHandlerFactoryOptions: { iceGatheringTimeout: 1000 },
            transportOptions: {
                server: this.voip.webSocketUrl,
                traceSip: isDebug,
            },
            uri: window.SIP.UserAgent.makeURI(`sip:${this._messaging.currentUser.res_users_settings_id.voip_username}@${this.voip.pbxAddress}`),
        };
    },
    /**
     * Initialises the ua, binds events and appends audio in the dom.
     *
     * @private
     */
    async _initUserAgent() {
        if (this.voip.mode === 'prod') {
            this.voip.triggerError(_t("Connecting..."));
            if (!this._messaging.device.hasRtcSupport || !navigator.mediaDevices) {
                this.voip.triggerError(_t("Your browser could not support WebRTC. Please check your configuration."));
                return;
            }
            this.voip.userAgent.update({ __sipJsUserAgent: this._createUserAgent() });
            if (!this.voip.userAgent.__sipJsUserAgent) {
                return;
            }
            try {
                await this.voip.userAgent.__sipJsUserAgent.start();
            } catch (_error) {
                this.voip.triggerError(_t("Failed to start the user agent. The URL of the websocket server may be wrong. Please have an administrator verify the websocket server URL in the General Settings."));
                return;
            }
            this.voip.userAgent.update({ registerer: {} });
            this.voip.userAgent.registerer.register();
        }
        this._configureDomElements();
    },
    /**
     * Triggers the sip invite.
     *
     * @private
     * @param {string} number
     */
    _makeCall(number) {
        if (this._callState !== CALL_STATE.NO_CALL) {
            return;
        }
        try {
            number = this._messaging.voip.cleanPhoneNumber(number);
            this._currentCallParams = { number };
            let calleeURI;
            if (this.voip.willCallFromAnotherDevice) {
                calleeURI = window.SIP.UserAgent.makeURI(`sip:${this.voip.cleanedExternalDeviceNumber}@${this.voip.pbxAddress}`);
                this._currentNumber = number;
            } else {
                calleeURI = window.SIP.UserAgent.makeURI(`sip:${number}@${this.voip.pbxAddress}`);
            }
            this._sipSession = new window.SIP.Inviter(this.voip.userAgent.__sipJsUserAgent, calleeURI);
            this._sipSession.delegate = this._getSessionDelegate();
            this._sipSession.stateChange.addListener((state) => this._onSessionStateChange(state));
            this._sipSession.invite({
                requestDelegate: {
                    onAccept: (response) => this._onOutgoingInvitationAccepted(response),
                    onProgress: (response) => this._onOutgoingInvitationProgress(response),
                    onReject: (response) => this._onOutgoingInvitationRejected(response),
                },
                sessionDescriptionHandlerOptions: {
                    constraints: { audio: true, video: false },
                },
            });
            this._isOutgoing = true;
            this._updateCallState(CALL_STATE.RINGING_CALL);
            this.voip.triggerError(_t("Please accept the use of the microphone."));
        } catch (err) {
            this.voip.triggerError(_t("The connection cannot be made.</br> Please check your configuration."));
            console.error(err);
        }
    },
    /**
     * Reject the inviteSession
     *
     * @private
     * @param {Object} inviteSession
     */
    _rejectInvite(inviteSession) {
        if (!this._isOutgoing) {
            this.voip.ringtoneRegistry.incomingCallRingtone.stop();
            inviteSession.reject({ statusCode: 603 });
        }
    },
    /**
     * TODO when the _sendNotification is moved into utils instead of mail.utils
     * remove this function and use the one in utils
     *
     * @private
     * @param {string} title
     * @param {string} content
     */
    _sendNotification(title, content) {
        if (
            window.Notification &&
            window.Notification.permission === 'granted' &&
            // Only send notifications in master tab, so that the user doesn't
            // get a notification for every open tab.
            this.call('multi_tab', 'isOnMainTab')
        ) {
            return new window.Notification(title, {
                body: content,
                icon: '/mail/static/src/img/odoo_o.png',
                silent: true,
            });
        }
    },
    /**
     * (Un)set the sound of audio media stream
     *
     * @private
     * @param {boolean} mute
     */
    _setMute(mute) {
        const call = this._sipSession;
        const peerConnection = call.sessionDescriptionHandler.peerConnection;
        if (peerConnection.getSenders) {
            for (const sender of peerConnection.getSenders()) {
                if (sender.track) {
                    sender.track.enabled = !mute;
                }
            }
        } else {
            for (const stream of peerConnection.getLocalStreams()) {
                for (const track of stream.getAudioTracks()) {
                    track.enabled = !mute;
                }
            }
        }
    },
    /**
     * Exits the `ongoing` state. In production mode, sends a BYE request to end
     * the current session.
     *
     * @private
     */
    _terminateSession() {
        if (this._sipSession && this._sipSession.state === window.SIP.SessionState.Established) {
            this._sipSession.bye();
        }
        this._sipSession = false;
        this._cleanRemoteAudio();
        this._updateCallState(CALL_STATE.NO_CALL);
        this._messaging.messagingBus.trigger('sip_bye');
    },
    _updateCallState(newState) {
        this._callState = newState;
        if (!mobile.methods.changeAudioMode) {
            return;
        }
        let mode = false;
        switch (this._callState) {
            case CALL_STATE.NO_CALL:
                mode = 'NO_CALL';
                break;
            case CALL_STATE.RINGING_CALL:
                mode = 'RINGING_CALL';
                break;
            case CALL_STATE.ONGOING_CALL:
                mode = 'CALL';
                break;
            case CALL_STATE.CANCELING_CALL:
            case CALL_STATE.REJECTING_CALL:
                // check if we are already in existing call
                mode = this._isOutgoing ? false : 'NO_CALL';
                break;
            default: // Don't update if call state set with an unknown value
                mode = false;
        }
        if (mode) {
            concurrency.delay(50).then(() => mobile.methods.changeAudioMode({mode}));
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Triggered when receiving a BYE request. Useful to detect when the callee
     * of an outgoing call hangs up.
     *
     * @private
     * @param {SIP.IncomingByeRequest} bye
     */
    _onBye({ incomingByeRequest: bye }) {
        this._sipSession = false;
        this._cleanRemoteAudio();
        this._updateCallState(CALL_STATE.NO_CALL);
        this._messaging.messagingBus.trigger('sip_bye');
    },
    /**
     * Triggered when the transport transitions from connected state.
     *
     * @private
     * @param {Error} error
     */
    _onDisconnect(error) {
        this.voip.triggerError(_t("The websocket connection with the server has been lost. Please try to refresh the page."));
    },
    /**
     * @private
     * @param {DOMException} error
     */
    _onGetUserMediaFailure(error) {
        const errorMessage = (() => {
            switch (error.name) {
                case 'NotAllowedError':
                    return _t("Cannot access audio recording device. If you have denied access to your microphone, please grant it and try again. Otherwise, make sure this website runs over HTTPS and that your browser is not set to deny access to media devices.");
                case 'NotFoundError':
                    return _t("No audio recording device available. The application requires a microphone in order to be used.");
                case 'NotReadableError':
                    return _t("A hardware error occured while trying to access audio recording device. Please make sure your drivers are up to date and try again.");
                default:
                    return sprintf(
                        _t("An error occured involving the audio recording device (%(errorName)s):</br>%(errorMessage)s"),
                        { errorMessage: error.message, errorName: error.name }
                    );
            }
        })();
        this.voip.triggerError(errorMessage, { isNonBlocking: true });
        if (this._isOutgoing) {
            this.hangup();
        } else {
            this.rejectIncomingCall();
        }
    },
    /**
     * @private
     * @param {MediaStream} stream
     */
    _onGetUserMediaSuccess(stream) {
        if (this._isOutgoing) {
            this._messaging.messagingBus.trigger('sip_error_resolved');
            this.voip.ringtoneRegistry.dialTone.play({ loop: true });
        } else {
            this._updateCallState(CALL_STATE.ONGOING_CALL);
            this._messaging.messagingBus.trigger('sip_incoming_call', this._currentCallParams);
        }
    },
    /**
     * Triggered when receiving CANCEL request.
     * Useful to handle missed phone calls.
     *
     * @private
     * @param {SIP.IncomingRequestMessage} message
     */
    _onIncomingInvitationCanceled(message) {
        this.voip.ringtoneRegistry.incomingCallRingtone.stop();
        if (this._notification) {
            this._notification.removeEventListener('close', this._rejectInvite, this._sipSession);
            this._notification.close();
            this._notification = undefined;
        }
        this._currentInviteSession.reject({ statusCode: 487 });
        this._messaging.messagingBus.trigger('sip_cancel_incoming', this._currentCallParams);
        this._sipSession = false;
        this._updateCallState(CALL_STATE.NO_CALL);
    },
    /**
     * Handles the invite event.
     *
     * @private
     * @param {Object} inviteSession
     */
    async _onInvite(inviteSession) {
        if (this._callState === CALL_STATE.ONGOING_CALL){
            // another session is active, therefore decline
            inviteSession.reject({ statusCode: 603 });
            return;
        }
        if (this._messaging.currentUser.res_users_settings_id.should_auto_reject_incoming_calls) {
            /**
             * 488: "Not Acceptable Here"
             * Request doesn't succeed but may succeed elsewhere.
             *
             * If the VOIP account is also associated to other tools, like a desk phone,
             * the invitation is refused on web browser but might be accepted on the desk phone.
             *
             * If the call is ignored on the desk phone, will receive status code 486: "Busy Here",
             * meaning the endpoint is unavailable.
             *
             * If the call is not accepted at all, no invite session will launch.
            */
            inviteSession.reject({ statusCode: 488 });
            return;
        }

        function sanitizedPhone(prefix, number) {
            if (number.startsWith("00")){
                return "+" + number.substr(2, number.length);
            }
            else if (number.startsWith("0")) {
                return "+" + prefix + number.substr(1, number.length);
            }
            /* USA exception for domestic numbers : In the US, the convention is 1 (area code)
             * extension, while in Europe it is (0 area code)/extension.
             */
            else if (number.startsWith("1")) {
                return "+" + number;
            }
        }

        let name = inviteSession.remoteIdentity.displayName;
        const number = inviteSession.remoteIdentity.uri.user;
        let numberSanitized = sanitizedPhone(inviteSession.remoteIdentity.uri.type, number);
        this._currentInviteSession = inviteSession;
        this._currentInviteSession.delegate = this._getSessionDelegate();
        this._currentInviteSession.incomingInviteRequest.delegate = {
            onCancel: (message) => this._onIncomingInvitationCanceled(message),
        };
        this._currentInviteSession.stateChange.addListener((state) => this._onSessionStateChange(state));
        let domain;
        if (numberSanitized) {
            domain = [
                '|', '|',
                ['sanitized_phone', 'ilike', number],
                ['sanitized_mobile', 'ilike', number],
                '|',
                ['sanitized_phone', 'ilike', numberSanitized],
                ['sanitized_mobile', 'ilike', numberSanitized],
            ];
        } else {
            domain = [
                '|',
                ['sanitized_phone', 'ilike', number],
                ['sanitized_mobile', 'ilike', number],
            ];
        }
        let contacts = await this._rpc({
            model: 'res.partner',
            method: 'search_read',
            domain: [['user_ids', '!=', false]].concat(domain),
            fields: ['id', 'display_name'],
        });
        if (!contacts.length) {
            contacts = await this._rpc({
                model: 'res.partner',
                method: 'search_read',
                domain: domain,
                fields: ['id', 'display_name'],
            });
        }
        /* Fallback if inviteSession.remoteIdentity.uri.type didn't give the correct country prefix
        */
        if (!contacts.length) {
            let lastSixDigitsNumber = number.substr(number.length - 6)
            contacts = await this._rpc({
                model: 'res.partner',
                method: 'search_read',
                domain: [
                    '|',
                    ['sanitized_phone', '=like', '%'+lastSixDigitsNumber],
                    ['sanitized_mobile', '=like', '%'+lastSixDigitsNumber],
                ],
                fields: ['id', 'display_name'],
            });
        }
        const incomingCallParams = { number };
        let contact = false;
        if (contacts.length) {
            contact = contacts[0];
            name = contact.display_name;
            incomingCallParams.partnerId = contact.id;
        }
        let content;
        if (name) {
            content = _.str.sprintf(_t("Incoming call from %s (%s)"), name, number);
        } else {
            content = _.str.sprintf(_t("Incoming call from %s"), number);
        }
        this._isOutgoing = false;
        this._updateCallState(CALL_STATE.RINGING_CALL);
        if (this.call('multi_tab', 'isOnMainTab')) {
            this.voip.ringtoneRegistry.incomingCallRingtone.play({ loop: true });
        }
        this._notification = this._sendNotification('Odoo', content);
        this._currentCallParams = incomingCallParams;
        this._messaging.messagingBus.trigger('incomingCall', incomingCallParams);

        if (!window.Notifcation || !window.Notification.requestPermission) {
           this._onWindowNotificationPermissionRequested({ content, inviteSession });
           return;
        }
        const res = window.Notification.requestPermission();
        if (!res) {
           this._onWindowNotificationPermissionRequested({ content, inviteSession });
           return;
        }
        res
            .then(permission => this._onWindowNotificationPermissionRequested({ content, inviteSession, permission }))
            .catch(() => this._onWindowNotificationPermissionRequested({ content, inviteSession }));
    },
    /**
     * Triggered when receiving a 2xx final response to the INVITE request.
     *
     * @private
     * @param {SIP.IncomingResponse} response
     * @param {function} response.ack
     * @param {SIP.IncomingResponseMessage} response.message
     * @param {SIP.SessionDialog} response.session
     */
    _onOutgoingInvitationAccepted(response) {
        this._updateCallState(CALL_STATE.ONGOING_CALL);
        this.voip.ringtoneRegistry.stopAll();
        if (
            this.voip.mode === 'prod' &&
            this._messaging.currentUser.res_users_settings_id.should_call_from_another_device &&
            this._currentNumber
        ) {
            this.transfer(this._currentNumber);
        } else {
            this._messaging.messagingBus.trigger('sip_accepted');
        }
    },
    /**
     * Triggered when receiving a 1xx provisional response to the INVITE
     * request (excepted code 100 responses).
     *
     * NOTE: Relying on provisional responses to implement behaviors seems like
     * a bad idea since they can be sent or not depending on the SIP server
     * implementation.
     *
     * @private
     * @param {SIP.IncomingResponse} response
     * @param {SIP.IncomingResponseMessage} response.message
     * @param {function} response.prack
     * @param {SIP.SessionDialog} response.session
     */
    _onOutgoingInvitationProgress(response) {
        const { statusCode } = response.message;
        if (statusCode === 183 /* Session Progress */ || statusCode === 180 /* Ringing */) {
            this.voip.ringtoneRegistry.dialTone.stop();
            this.voip.ringtoneRegistry.ringbackTone.play({ loop: true });
            this._messaging.messagingBus.trigger('changeStatus');
        }
    },
    /**
     * Triggered when receiving a 4xx, 5xx, or 6xx final response to the
     * INVITE request.
     *
     * @private
     * @param {SIP.IncomingResponse} response
     * @param {SIP.IncomingResponseMessage} response.message
     * @param {number} response.message.statusCode
     * @param {string} response.message.reasonPhrase
     */
    _onOutgoingInvitationRejected(response) {
        if (response.message.statusCode === 487) { // Request Terminated
            // Don't show an error when the user hung up on their own.
            return;
        }
        this._sipSession = false;
        this.voip.ringtoneRegistry.stopAll();
        this._updateCallState(CALL_STATE.NO_CALL);
        const errorMessage = (() => {
            switch (response.message.statusCode) {
                case 404: // Not Found
                case 488: // Not Acceptable Here
                case 603: // Decline
                    return sprintf(
                        _t("The number is incorrect, the user credentials could be wrong or the connection cannot be made. Please check your configuration.</br> (Reason received: %(reasonPhrase)s)"),
                        { reasonPhrase: escape(response.message.reasonPhrase) }
                    );
                case 486: // Busy Here
                case 600: // Busy Everywhere
                    return _t("The person you try to contact is currently unavailable.");
                default:
                    return sprintf(
                        _t(`Call rejected (reason: "%(reasonPhrase)s")`),
                        { reasonPhrase: escape(response.message.reasonPhrase) }
                    );
            }
        })();
        this.voip.triggerError(errorMessage, { isNonBlocking: true });
        this._messaging.messagingBus.trigger('sip_cancel_outgoing');
    },
    /**
     * Triggered when receiving a response with status code 2xx to the REFER
     * request.
     *
     * @private
     * @param {SIP.IncomingResponse} response The server final response to the
     * REFER request.
     */
    _onReferAccepted(response) {
        this._terminateSession();
    },
    /**
     * @private
     * @param {SIP.SessionState} newState
     */
    _onSessionStateChange(newState) {
        switch (newState) {
            case window.SIP.SessionState.Initial:
                break;
            case window.SIP.SessionState.Establishing:
                break;
            case window.SIP.SessionState.Established:
                this._configureRemoteAudio();
                this._sipSession.sessionDescriptionHandler.remoteMediaStream.onaddtrack = (mediaStreamTrackEvent) => this._configureRemoteAudio();
                break;
            case window.SIP.SessionState.Terminating:
                break;
            case window.SIP.SessionState.Terminated:
                break;
            default:
                throw new Error("Unknown session state.");
        }
    },
    /**
     * @private
     * @param {Object} param0
     * @param {string} param0.content
     * @param {Object} param0.inviteSession
     * @param {string} [param0.permission]
     */
    _onWindowNotificationPermissionRequested({
        content,
        inviteSession,
        permission,
    }) {
        if (permission === 'granted') {
            this._notification = this._sendNotification("Odoo", content);
            if (this._notification) {
                this._notification.onclick = function () {
                    window.focus();
                    this.close();
                };
                this._notification.removeEventListener('close', this._rejectInvite, inviteSession);
            }
        }
    },
});

return UserAgent;

});
