odoo.define('voip.DialingPanel', function (require) {
"use strict";

const PhoneCallActivitiesTab = require('voip.PhoneCallActivitiesTab');
const PhoneCallContactsTab = require('voip.PhoneCallContactsTab');
const PhoneCallRecentTab = require('voip.PhoneCallRecentTab');
const UserAgent = require('voip.UserAgent');

const core = require('web.core');
const config = require('web.config');
const Dialog = require('web.Dialog');
const dom = require('web.dom');
const mobile = require('web_mobile.core');
const { sprintf } = require('@web/core/utils/strings');
const Widget = require('web.Widget');

const { _t, _lt } = core;
const YOUR_ARE_ALREADY_IN_A_CALL = _lt("You are already in a call");

const DialingPanel = Widget.extend({
    template: 'voip.DialingPanel',
    events: {
        'click .o_dial_accept_button': '_onClickAcceptButton',
        'click .o_dial_call_button': '_onClickCallButton',
        'click .o_dial_fold': '_onClickFold',
        'click .o_dial_hangup_button': '_onClickHangupButton',
        'click .o_dial_keypad_backspace': '_onClickKeypadBackspace',
        'click .o_dial_postpone_button': '_onClickPostponeButton',
        'click .o_dial_reject_button': '_onClickRejectButton',
        'click .o_dial_tabs .o_dial_tab': '_onClickTab',
        'click .o_dial_keypad_icon': '_onClickDialKeypadIcon',
        'click .o_dial_number': '_onClickDialNumber',
        'click .o_dial_window_close': '_onClickWindowClose',
        'input .o_dial_search_input': '_onInputSearch',
        'keyup .o_dial_keypad_input': '_onKeyupKeypadInput',
    },
    custom_events: {
        'fold_panel': '_onFoldPanel',
        'muteCall': '_onMuteCall',
        'resetMissedCalls': '_resetMissedCalls',
        'showHangupButton': '_onShowHangupButton',
        'switch_keypad': '_onSwitchKeypad',
        'unmuteCall': '_onUnmuteCall',
    },
    /**
     * @constructor
     */
    init() {
        this._super(...arguments);

        this._isFolded = false;
        this._isFoldedBeforeCall = false;
        this._isInCall = false;
        this._isMobileDevice = config.device.isMobileDevice;
        this._isPostpone = false;
        this._isShow = false;
        this._isWebRTCSupport = window.RTCPeerConnection && window.MediaStream && navigator.mediaDevices;
        this._onInputSearch = _.debounce(this._onInputSearch.bind(this), 500);
        this._onBackButton = this._onBackButton.bind(this);
        this._tabs = {
            contacts: new PhoneCallContactsTab(this),
            nextActivities: new PhoneCallActivitiesTab(this),
            recent: new PhoneCallRecentTab(this),
        };
        this._missedCounter = 0; // amount of missed call
        this._onChangeStatus = this._onChangeStatus.bind(this);
        this._onIncomingCall = this._onIncomingCall.bind(this);
        this._onSipAccepted = this._onSipAccepted.bind(this);
        this._onSipBye = this._onSipBye.bind(this);
        this._onSipCancelIncoming = this._onSipCancelIncoming.bind(this);
        this._onSipCancelOutgoing = this._onSipCancelOutgoing.bind(this);
        this._onSipError = this._onSipError.bind(this);
        this._onSipErrorResolved = this._onSipErrorResolved.bind(this);
        this._onSipIncomingCall = this._onSipIncomingCall.bind(this);
        this._onSipRejected = this._onSipRejected.bind(this);
        this.title = this._getTitle();
    },
    async willStart() {
        this._messaging = await owl.Component.env.services.messaging.get();
    },
    /**
     * @override
     */
    async start() {
        this._$callButton = this.$('.o_dial_call_button');
        this._$incomingCallButtons = this.$('.o_dial_incoming_buttons');
        this._$keypad = this.$('.o_dial_keypad');
        this._$keypadInput = this.$('.o_dial_keypad_input');
        this._$keypadInputDiv = this.$('.o_dial_keypad_input_div');
        this._$mainButtons = this.$('.o_dial_main_buttons');
        this._$postponeButton = this.$('.o_dial_postpone_button');
        this._$searchBar = this.$('.o_dial_searchbar');
        this._$searchInput = this.$('.o_dial_search_input');
        this._$tabsPanel = this.$('.o_dial_panel');
        this._$tabs = this.$('.o_dial_tabs');

        this._fetchMissedCallFromServer();

        this._activeTab = this._tabs.nextActivities;
        await this._tabs.contacts.appendTo(this.$('.o_dial_contacts'));
        await this._tabs.nextActivities.appendTo(this.$('.o_dial_next_activities'));
        await this._tabs.recent.appendTo(this.$('.o_dial_recent'));

        this.$el.hide();
        this._$incomingCallButtons.hide();
        this._$keypad.hide();

        this._messaging.messagingBus.addEventListener('changeStatus', this._onChangeStatus);
        this._messaging.messagingBus.addEventListener('incomingCall', this._onIncomingCall);
        this._messaging.messagingBus.addEventListener('sip_accepted', this._onSipAccepted);
        this._messaging.messagingBus.addEventListener('sip_bye', this._onSipBye);
        this._messaging.messagingBus.addEventListener('sip_cancel_incoming', this._onSipCancelIncoming);
        this._messaging.messagingBus.addEventListener('sip_cancel_outgoing', this._onSipCancelOutgoing);
        this._messaging.messagingBus.addEventListener('sip_error', this._onSipError);
        this._messaging.messagingBus.addEventListener('sip_error_resolved', this._onSipErrorResolved);
        this._messaging.messagingBus.addEventListener('sip_incoming_call', this._onSipIncomingCall);
        this._messaging.messagingBus.addEventListener('sip_rejected', this._onSipRejected);
        /**
         * UserAgent must be created after the event listeners have been added
         * so that errors triggered during the initialization of the user agent
         * using sip_error are caught.
         */
        this._messaging.voip.update({
            userAgent: {
                legacyUserAgent: new UserAgent(this),
            },
        });
        core.bus.on('transfer_call', this, this._onTransferCall);
        core.bus.on('voip_onToggleDisplay', this, function () {
            this._resetMissedCalls();
            this._onToggleDisplay();
        });

        this.call('bus_service', 'addEventListener', 'notification', this._onBusNotification.bind(this));

        for (const tab of Object.values(this._tabs)) {
            tab.on('callNumber', this, ev => this._makeCall(ev.data.number));
            tab.on('hidePanelHeader', this, () => this._hideHeader());
            tab.on('showPanelHeader', this, () => this._showHeader());
        }
    },
    destroy() {
        this._messaging.messagingBus.removeEventListener('changeStatus', this._onChangeStatus);
        this._messaging.messagingBus.removeEventListener('incomingCall', this._onIncomingCall);
        this._messaging.messagingBus.removeEventListener('sip_accepted', this._onSipAccepted);
        this._messaging.messagingBus.removeEventListener('sip_bye', this._onSipBye);
        this._messaging.messagingBus.removeEventListener('sip_cancel_incoming', this._onSipCancelIncoming);
        this._messaging.messagingBus.removeEventListener('sip_cancel_outgoing', this._onSipCancelOutgoing);
        this._messaging.messagingBus.removeEventListener('sip_error', this._onSipError);
        this._messaging.messagingBus.removeEventListener('sip_error_resolved', this._onSipErrorResolved);
        this._messaging.messagingBus.removeEventListener('sip_incoming_call', this._onSipIncomingCall);
        this._messaging.messagingBus.removeEventListener('sip_rejected', this._onSipRejected);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Function called when a phonenumber is clicked in the activity widget.
     *
     * @param {Object} params
     * @param {string} params.number
     * @param {integer} params.activityId
     * @return {Promise}
     */
    async callFromActivityWidget(params) {
        if (!this._isInCall) {
            this.$(`
                .o_dial_tab.active,
                .tab-pane.active`
            ).removeClass('active');
            this.$(`
                .o_dial_activities_tab .o_dial_tab,
                .tab-pane.o_dial_next_activities`
            ).addClass('active');
            this._activeTab = this._tabs.nextActivities;
            await this._activeTab.callFromActivityWidget(params);
            return this._makeCall(params.number);
        } else {
            this.displayNotification({ title: YOUR_ARE_ALREADY_IN_A_CALL });
        }
    },
    /**
     * Function called when widget phone is clicked.
     *
     * @param {Object} params
     * @param {string} params.number
     * @param {string} params.resModel
     * @param {integer} params.resId
     * @return {Promise}
     */
    async callFromPhoneWidget(params) {
        if (!this._isInCall) {
            this.$(`
                .o_dial_tab.active,
                .tab-pane.active`
            ).removeClass('active');
            this.$(`
                .o_dial_recent_tab .o_dial_tab,
                .tab-pane.o_dial_recent`
            ).addClass('active');
            this._activeTab = this._tabs.recent;
            const phoneCall = await this._activeTab.callFromPhoneWidget(params);
            return this._makeCall(params.number, phoneCall);
        } else {
            this.displayNotification({ title: YOUR_ARE_ALREADY_IN_A_CALL });
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Block the VOIP widget
     *
     * @private
     * @param {string} message  The message we want to show when blocking the
     *   voip widget
     */
    _blockOverlay(message) {
        this._$tabsPanel.block({ message });
        this._$mainButtons.block();
        this.$('.blockOverlay').addClass('cursor-default');
        this.$('.blockMsg').addClass('w-50 mx-auto end-0 start-0 text-white cursor-default');
    },
    /**
     * @private
     */
    _cancelCall() {
        $('.o_dial_transfer_button').popover('hide');
        this.$el.css('zIndex', '');
        this._isInCall = false;
        this._isPostpone = false;
        this._hidePostponeButton();
        this._showCallButton();
        this._resetMainButton();
    },
    /**
     * @private
     */
    _fold() {
        $('.o_dial_transfer_button').popover('hide');
        if (this._isFolded) {
            this.$el.addClass('folded');
            this.$('.o_dial_main_buttons').hide();
            this.$('.o_dial_incoming_buttons').hide();
        } else {
            this.$el.removeClass('folded');
            this.$('.o_dial_main_buttons').show();
        }
    },
    /**
     * @private
     * @returns {string}
     */
    _getTitle() {
        switch (this._missedCounter) {
            case 0:
                return _t("VoIP");
            case 1:
                return _t("1 missed call");
            case 2:
                return _t("2 missed calls");
            default:
                return sprintf(
                    _t("%(number of missed calls)s missed calls"),
                    { 'number of missed calls': this._missedCounter }
                );
        }
    },
    /**
     * Hides the search input and the tabs.
     *
     * @private
     */
    _hideHeader() {
        this._$searchBar.hide();
        this._$tabs.parent().hide();
    },
    /**
     * @private
     */
    _hidePostponeButton() {
        this._$postponeButton.hide();
    },
    /**
     * @private
     * @param {string} number
     * @param {voip.PhonenCall} [phoneCall] if the event function already created a
     *   phonecall; this phonecall is passed to the initPhoneCall function in
     *   order to not create a new one.
     * @return {Promise}
     */
    async _makeCall(number, phoneCall) {
        if (!this._isInCall) {
            if (!await this._useVoip()) {
                // restore the default browser behavior
                const $a = $('<a/>', {
                    href: `tel:${number}`,
                    style: "display:none"
                }).appendTo(document.body);
                $a[0].click();
                $a.remove();
                return;
            }
            if (!this._isWebRTCSupport) {
                this.displayNotification({ title: _t("Your browser could not support WebRTC. Please check your configuration.") });
                return;
            }
            if (!number) {
                this.displayNotification({ message: _t("The phonecall has no number") });
                return;
            }
            if (!this._isShow || this._isFolded) {
                await this._toggleDisplay();
            }
            await this._activeTab.initPhoneCall(phoneCall);
            this._messaging.voip.userAgent.legacyUserAgent.makeCall(number);
            this._isInCall = true;
        } else {
            this.displayNotification({ title: YOUR_ARE_ALREADY_IN_A_CALL });
        }
    },
    /**
     * start a call on ENTER keyup
     *
     * @private
     * @param {KeyEvent} ev
     */
    _onKeyupKeypadInput(ev) {
        if (ev.keyCode === $.ui.keyCode.ENTER) {
            this._onClickCallButton();
        }
    },
    /**
     * @private
     */
    async _fetchMissedCallFromServer() {
        const missedCalls = await this._rpc({
            model: 'voip.phonecall',
            method: 'get_missed_call_info'
        });
        this._missedCounter = missedCalls[0];
        this._refreshMissedCalls();
        if (this._missedCounter > 0) {
            this._showWidgetFolded();
            this.$('.o_dial_tab.active, .tab-pane.active').removeClass('active');
            this.$('.o_dial_recent_tab .o_dial_tab, .tab-pane.o_dial_recent').addClass('active');
            this._activeTab = this._tabs.recent;
        }
    },
    /**
     * Refresh the header with amount of missed calls
     *
     * @private
     */
    _refreshMissedCalls() {
        this.title = this._getTitle();
        $('.o_dial_text').text(this.title);
    },
    /**
     * Refreshes the phonecall list of the active tab.
     *
     * @private
     * @return {Promise}
     */
    async _refreshPhoneCallsStatus() {
        if (this._isInCall) {
            return;
        }
        return this._activeTab.refreshPhonecallsStatus();
    },
    /**
     * @private
     */
    _resetMainButton() {
        this._$mainButtons.show();
        this._$incomingCallButtons.hide();
    },
    /**
     * Reset to 0 amount of missed calls
     *
     * @private
     */
    _resetMissedCalls(data={'data': {'forceReset': false}}) {
        if (this._missedCounter > 0 && (data['data']['forceReset'] || (this._isFolded && this._isShow))) {
            this._missedCounter = 0;
            this._rpc({
                model: 'res.users',
                method: 'reset_last_seen_phone_call',
            });
            this._refreshMissedCalls();
        }
    },
    /**
     * @private
     */
    _showCallButton() {
        this._resetMainButton();
        this._$callButton.addClass('o_dial_call_button');
        this._$callButton.removeClass('o_dial_hangup_button text-danger');
        this._$callButton[0].setAttribute('aria-label', _t('Call'));
        this._$callButton[0].title = _t('Call');
    },
    /**
     * @private
     */
    _showHangupButton() {
        this._resetMainButton();
        this._$callButton.removeClass('o_dial_call_button');
        this._$callButton.addClass('o_dial_hangup_button text-danger');
        this._$callButton[0].setAttribute('aria-label', _t('End Call'));
        this._$callButton[0].title = _t('End Call');
    },
    /**
     * Shows the search input and the tabs.
     *
     * @private
     */
    _showHeader() {
        this._$searchBar.show();
        this._$tabs.parent().show();
    },
    /**
     * @private
     */
    _showPostponeButton() {
        this._$postponeButton.show();
    },
    /**
     * @private
     * @return {Promise}
     */
    async _showWidget() {
        if (!this._isShow) {
            this.$el.show();
            this._isShow = true;
            mobile.backButtonManager.addListener(this, this._onBackButton);
            this._isFolded = false;
            if (this._isWebRTCSupport) {
                this._$searchInput.focus();
            }
        }
        if (this._isFolded) {
            return this._toggleFold({ isFolded: false });
        }
    },
    /**
     * @private
     * @return {Promise}
     */
    async _showWidgetFolded() {
        if (!this._isShow) {
            this.$el.show();
            this._isShow = true;
            this._isFolded = true;
            this._fold(false);
        }
    },
    /**
     * @private
     * @return {Promise}
     */
    async _toggleDisplay() {
        $('.o_dial_transfer_button').popover('hide');
        if (this._isShow) {
            if (!this._isFolded) {
                this.$el.hide();
                this._isShow = false;
                mobile.backButtonManager.removeListener(this, this._onBackButton);
            } else {
                return this._toggleFold({ isFolded: false });
            }
        } else {
            this.$el.show();
            this._isShow = true;
            mobile.backButtonManager.addListener(this, this._onBackButton);
            if (this._isFolded) {
                await this._toggleFold();
            }
            this._isFolded = false;
            if (this._isWebRTCSupport) {
                this._$searchInput.focus();
            }
        }
    },
    /**
     * @private
     * @param {Object} [param0={}]
     * @param {boolean} [param0.isFolded]
     * @return {Promise}
     */
    async _toggleFold({ isFolded }={}) {
        if (!config.device.isMobile) {
            if (this._isFolded) {
                await this._refreshPhoneCallsStatus();
            }
            this._isFolded = _.isBoolean(isFolded) ? isFolded : !this._isFolded;
            this._fold();
        }
        mobile.backButtonManager[this._isFolded ? 'removeListener' : 'addListener'](this, this._onBackButton);
    },
    /**
     * @private
     */
    _toggleKeypadInputDiv() {
        this._$keypadInputDiv.show();
        if (this._isWebRTCSupport) {
            this._$keypadInput.focus();
        }
    },
    /**
     * Unblock the VOIP widget
     *
     * @private
     */
    _unblockOverlay() {
        this._$tabsPanel.unblock();
        this._$mainButtons.unblock();
    },
    /**
     * Check if the user wants to use voip to make the call.
     * It's check the value res_user field `how_to_call_on_mobile` and
     * ask to the end user is choice and update the value as needed
     * @return {Promise<boolean>}
     * @private
     */
    async _useVoip() {
        // Only for mobile device
        if (!config.device.isMobileDevice) {
            return true;
        }

        const mobileCallMethod = this._messaging.currentUser.res_users_settings_id.how_to_call_on_mobile;
        // avoid ask choice if value is set
        if (mobileCallMethod !== 'ask') {
            return mobileCallMethod === 'voip';
        }

        const useVOIP = await new Promise(resolve => {
            const $content = $('<main/>', {
                role: 'alert',
                text: _t("Make a call using:")
            });

            const $checkbox = dom.renderCheckbox({
                text: _t("Remember ?"),
            }).addClass('mb-0');

            $content.append($checkbox);

            const processChoice = useVoip => {
                if ($checkbox.find('input[type="checkbox"]').is(':checked')) {
                    this._messaging.voip.userAgent.legacyUserAgent.updateCallPreference(useVoip ? 'voip' : 'phone');
                }
                resolve(useVoip);
            };

            new Dialog(this, {
                size: 'medium',
                fullscreen: false,
                buttons: [{
                    text: _t("Voip"),
                    close: true,
                    click: () => processChoice(true),
                }, {
                    text: _t("Phone"),
                    close: true,
                    click: () => processChoice(false),
                }],
                $content: $content,
                renderHeader: false,
            }).open({shouldFocusButtons: true});
        });
        if (useVOIP && mobile.methods.setupVoip) {
            const hasMicroPhonePermission = await mobile.methods.setupVoip();
            if (!hasMicroPhonePermission) {
                await new Promise(resolve => Dialog.alert(this, _t("You must allow the access to the microphone on your device. Otherwise, the VoIP call receiver will not hear you."), {
                    confirm_callback: resolve,
                }));
            }
        }
        return useVOIP;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------
    /**
     * Bind directly the DialingPanel#_onClickWindowClose method to the
     * 'backbutton' event.
     *
     * @private
     * @override
     */
    _onBackButton(ev) {
        this._onClickWindowClose(ev);
    },
    /**
     * @private
     */
    _onChangeStatus() {
        this._activeTab.changeRinging();
    },
    /**
     * @private
     */
    _onClickAcceptButton() {
        this._messaging.voip.userAgent.legacyUserAgent.acceptIncomingCall();
        this._$mainButtons.show();
        this._$incomingCallButtons.hide();
    },
    /**
     * Method handeling the click on the call button.
     * If a phonecall detail is displayed, then call its first number.
     * If there is a search value, we call it.
     * If we are on the keypad and there is a value, we call it.
     *
     * @private
     * @return {Promise}
     */
    async _onClickCallButton() {
        if (this._isInCall) {
            return;
        }
        if (this.$('.o_phonecall_details').is(':visible')) {
            this._activeTab.callFirstNumber();
            if (this._activeTab.isAutoCallMode) {
                this._showPostponeButton(); //TODO xdo, should be triggered from tab
            }
            return;
        } else if (this._$tabsPanel.is(':visible')) {
            return this._activeTab.callFromTab();
        } else {
            const number = this._$keypadInput.val();
            if (!number) {
                return;
            }
            this._onToggleKeypad();
            this.$(`
                .o_dial_tab.active,
                .tab-pane.active`
            ).removeClass('active');
            this.$(`
                .o_dial_recent_tab .o_dial_tab,
                .tab-pane.o_dial_recent`
            ).addClass('active');
            this._activeTab = this._tabs.recent;
            const phoneCall = await this._activeTab.callFromNumber(number);
            await this._makeCall(number, phoneCall);
            this._$keypadInput.val("");
        }
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickDialKeypadIcon(ev) {
        ev.preventDefault();
        this._onToggleKeypad();
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickDialNumber(ev) {
        ev.preventDefault();
        this._$keypadInput.focus();
        this._onKeypadButtonClick(ev.currentTarget.textContent);
    },
    /**
     * @private
     * @return {Promise}
     */
    async _onClickFold() {
        if (this._isFolded) {
            this._resetMissedCalls();
        }
        return this._toggleFold();
    },
    /**
     * @private
     */
    _onClickHangupButton() {
        this._messaging.voip.userAgent.legacyUserAgent.hangup();
        this._cancelCall();
        this._activeTab._selectPhoneCall(this._activeTab._currentPhoneCallId);
    },
    /**
     * @private
     */
    _onClickKeypadBackspace() {
        this._$keypadInput.val(this._$keypadInput.val().slice(0, -1));
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickPostponeButton(ev) {
        if (!this._isInCall) {
            return;
        }
        this._isPostpone = true;
        this._messaging.voip.userAgent.legacyUserAgent.hangup();
    },
    /**
     * @private
     */
    _onClickRejectButton() {
        this.$el.css('zIndex', '');
        this._messaging.voip.userAgent.legacyUserAgent.rejectIncomingCall();
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    async _onClickTab(ev) {
        ev.preventDefault();
        this._activeTab = this._tabs[ev.currentTarget.getAttribute('aria-controls')];
        this._$searchInput.val("");
        return this._refreshPhoneCallsStatus();
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickWindowClose(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        $('.o_dial_transfer_button').popover('hide');
        this.$el.hide();
        this._isShow = false;
        mobile.backButtonManager.removeListener(this, this._onBackButton);
    },
    /**
     * @private
     * @param {Object} detail contains the number and the partnerId of the caller.
     * @param {string} detail.number
     * @param {integer} detail.partnerId
     * @return {Promise}
     */
    async _onIncomingCall({ detail }) {
        this._isFoldedBeforeCall = this._isShow ? this._isFolded : true;
        await this._showWidget();
        this._$keypad.hide();
        this._$tabsPanel.show();
        this.$(`
            .o_dial_tab.active,
            .tab-pane.active`
        ).removeClass('active');
        this.$(`
            .o_dial_recent_tab .o_dial_tab,
            .tab-pane.o_dial_recent`
        ).addClass('active');
        this.$el.css('zIndex', 1051);
        this._activeTab = this._tabs.recent;
        await this._activeTab.onIncomingCall(detail);
        this._$mainButtons.hide();
        this._$incomingCallButtons.show();
    },
    /**
     * @private
     * @param {OdooEvent} ev
     * @return {Promise}
     */
    _onFoldPanel(ev) {
        return this._toggleFold();
    },
    /**
     * @private
     * @param {OdooEvent} ev
     * @return {Promise}
     */
    _onInputSearch(ev) {
        return this._activeTab.searchPhoneCall($(ev.currentTarget).val());
    },
    /**
     * @private
     * @param {string} number the keypad number clicked
     */
    _onKeypadButtonClick(number) {
        if (this._isInCall) {
            this._messaging.voip.userAgent.legacyUserAgent.sendDtmf(number);
        }
        this._$keypadInput.val(this._$keypadInput.val() + number);
    },
    /**
     * @private
     * @param {CustomEvent} ev
     * @param {Object[]} [ev.detail] notifications coming from the bus.
     * @param {string} [ev.detail[i].type]
     */
    async _onBusNotification({ detail: notifications }) {
        for (const { type } of notifications) {
            if (type === 'refresh_voip') {
                if (this._isInCall) {
                    return;
                }
                if (this._activeTab === this._tabs.nextActivities) {
                    await this._activeTab.refreshPhonecallsStatus();
                }
            }
        }
    },
    /**
     * @private
     */
    _onMuteCall() {
        this._messaging.voip.userAgent.legacyUserAgent.muteCall();
    },
    /**
     * @private
     */
    async _onNotificationRefreshVoip() {
        if (this._isInCall) {
            return;
        }
        if (this._activeTab !== this._tabs.nextActivities) {
            return;
        }
        return this._activeTab.refreshPhonecallsStatus();
    },
    /**
     * @private
     */
    _onShowHangupButton() {
        this._showHangupButton();
    },
    /**
     * @private
     */
    _onSipAccepted() {
        this._activeTab.onCallAccepted();
    },
    /**
     * @private
     */
    async _onSipBye() {
        this._isInCall = false;
        this._showCallButton();
        this._hidePostponeButton();
        const isDone = !this._isPostpone;
        this._isPostpone = false;
        this.$el.css('zIndex', '');
        return this._activeTab.hangupPhonecall(isDone);
    },
    /**
     * @private
     * @param {Object} detail contains the number and the partnerId of the caller
     * @param {string} detail.number
     * @param {integer} detail.partnerId
     * @return {Promise}
     */
    _onSipCancelIncoming({ detail }) {
        this._isInCall = false;
        this._isPostpone = false;
        this._missedCounter = this._missedCounter + 1;
        this._refreshMissedCalls();
        this.$el.css('zIndex', '');

        if (this._isFoldedBeforeCall) {
            this._activeTab.onMissedCall(detail);
            this.$('.o_dial_tab.active, .tab-pane.active').removeClass('active');
            this.$('.o_dial_recent_tab .o_dial_tab, .tab-pane.o_dial_recent').addClass('active');
            this._activeTab = this._tabs.recent;
            this._isFolded = true;
            this._fold();
        } else {
            this._hidePostponeButton();
            this._showCallButton();
            this._resetMainButton();
            return this._activeTab.onMissedCall(detail, true);
        }
    },
    /**
     * @private
     */
    _onSipCancelOutgoing() {
        this._cancelCall();
        this._activeTab.onCancelOutgoingCall();
    },
    /**
     * @private
     * @param {Object} detail
     * @param {Object} detail.isNonBlocking Set to true if the error should not
     * block the UI.
     * @param {Object} detail.message contains the message to display on the
     *   gray overlay
     */
    _onSipError({ detail }) {
        const message = detail.message;
        this._isInCall = false;
        this._isPostpone = false;
        this._hidePostponeButton();
        this._blockOverlay(message);
        if (detail.isNonBlocking) {
            this.$('.blockOverlay').on('click', () => this._onSipErrorResolved());
            this.$('.blockOverlay').attr('title', _t("Click to unblock"));
        }
    },
    /**
     * @private
     */
    _onSipErrorResolved() {
        this._unblockOverlay();
    },
    /**
     * @private
     * @param {Object} detail contains the number and the partnerId of the caller
     * @param {string} detail.number
     * @param {integer} detail.partnerId
     * @return {Promise}
     */
    async _onSipIncomingCall({ detail }) {
        this._onSipErrorResolved();
        if (this._isInCall) {
            return;
        }
        this._isInCall = true;
        this.$(`
            .o_dial_tab.active,
            .tab-pane.active`
        ).removeClass('active');
        this.$(`
            .o_dial_recent_tab .o_dial_tab,
            .tab-pane.o_dial_recent`
        ).addClass('active');
        this.$el.css('zIndex', 1051);
        this._activeTab = this._tabs.recent;
        await this._activeTab.onIncomingCallAccepted(detail);
        this._showHangupButton();
    },
    /**
     * @private
     * @param {Object} detail contains the number and the partnerId of the caller.
     * @param {string} detail.number
     * @param {integer} detail.partnerId
     * @return {Promise}
     */
    _onSipRejected({ detail }) {
        this._cancelCall();
        return this._activeTab.onRejectedCall(detail);
    },
    /**
     * @private
     */
    _onSwitchKeypad() {
        this._$keypadInput.val(this._$searchInput.val());
        this._onToggleKeypad();
    },
    /**
     * @private
     */
    async _onToggleDisplay() {
        await this._toggleDisplay();
        return this._refreshPhoneCallsStatus();
    },
    /**
     * @private
     */
    _onToggleKeypad() {
        $('.o_dial_transfer_button').popover('hide');
        if (this._$tabsPanel.is(":visible")) {
            this._$tabsPanel.hide();
            this._$keypad.show();
            this._toggleKeypadInputDiv();
        } else {
            this._$tabsPanel.show();
            this._$keypad.hide();
        }
    },
    /**
     * @private
     * @param {string} number
     */
    _onTransferCall(number) {
        this._messaging.voip.userAgent.legacyUserAgent.transfer(number);
    },
    /**
     * @private
     */
    _onUnmuteCall() {
        this._messaging.voip.userAgent.legacyUserAgent.unmuteCall();
    },
});

return DialingPanel;

});
