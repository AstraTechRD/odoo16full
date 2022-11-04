odoo.define('voip.PhoneCallDetails', function (require) {
"use strict";

const config = require('web.config');
const core = require('web.core');
const session = require('web.session');
const Widget = require('web.Widget');

const { Component } = owl;

const QWeb = core.qweb;

function cleanNumber(number) {
    if (!number) {
        return
    }
    return number.replace(/[^0-9+]/g, '');
}

const PhoneCallDetails = Widget.extend({
    template: 'voip.PhoneCallDetails',
    events: {
        'click .o_dial_activity_done': '_onClickActivityDone',
        'click .o_dial_call_number': '_onClickCallNumber',
        'click .o_dial_activity_cancel': '_onClickCancel',
        'click .o_phonecall_details_close': '_onClickDetailsClose',
        'click .o_dial_email': '_onClickEmail',
        'click .o_dial_log': '_onClickLog',
        'click .o_dial_mute_button': '_onClickMuteButton',
        'click .o_dial_reschedule_activity': '_onClickRescheduleActivity',
        'click .o_dial_to_partner': '_onClickToPartner',
        'click .o_dial_to_record': '_onClickToRecord',
    },
    /**
     * TODO: reduce coupling between PhoneCallDetails & PhoneCall
     *
     * @override
     * @param {voip.PhoneCallTab} parent
     * @param {voip.PhoneCall} phoneCall
     */
    init(parent, phoneCall) {
        this._super(...arguments);

        this.activityId = phoneCall.activityId;
        this.activityResId = phoneCall.activityResId;
        this.activityModelName = phoneCall.activityModelName;
        this.date = phoneCall.date;
        this.durationSeconds = 0;
        this.email = phoneCall.email;
        this.id = phoneCall.id;
        this.imageSmall = phoneCall.imageSmall;
        this.minutes = phoneCall.minutes;
        this.mobileNumber = phoneCall.mobileNumber;
        this.name = phoneCall.name;
        this.partnerId = phoneCall.partnerId;
        this.partnerName = phoneCall.partnerName;
        this.phoneNumber = phoneCall.phoneNumber;
        this.seconds = phoneCall.seconds;
        this.state = phoneCall.state;

        this._$closeDetails = undefined;
        this._$muteButton = undefined;
        this._$muteIcon = undefined;
        this._$phoneCallActivityButtons = undefined;
        this._$phoneCallDetails = undefined;
        this._$phoneCallInCall = undefined;
        this._$phoneCallInfo = undefined;
        this._$phoneCallReceivingCall = undefined;
        this._activityResModel = phoneCall.activityResModel;
        this._isMuted = false;
    },
    /**
     * @override
     */
    start() {
        this._super(...arguments);

        this._$closeDetails = this.$('.o_phonecall_details_close');
        this._$muteButton = this.$('.o_dial_mute_button');
        this._$muteIcon = this.$('.o_dial_mute_button .fa');
        this._$phoneCallActivityButtons = this.$('.o_phonecall_activity_button');
        this._$phoneCallDetails = this.$('.o_phonecall_details');
        this._$phoneCallInCall = this.$('.o_phonecall_in_call');
        this._$phoneCallInfoName = this.$('.o_phonecall_info_name');
        this._$phoneCallInfo = this.$('.o_phonecall_info');
        this._$phoneCallReceivingCall = this.$('.o_dial_incoming_buttons');

        this._$muteButton.attr('disabled', 'disabled');
        this.$('.o_dial_transfer_button').attr('disabled', 'disabled');

        this._onInputNumberDebounced = _.debounce(this._onInputNumber.bind(this), 350);

        var self = this;
        var number = this.getParent().getParent()._messaging.voip.cleanedExternalDeviceNumber;
        $('.o_dial_transfer_button').popover({
            placement: 'top',
            delay: {show: 0, hide: 100},
            title: 'Transfer to' + '<button class="btn-close float-end"></button>',
            container: 'body',
            html: true,
            content: function(){
                var $content = $(QWeb.render('voip.PhoneCallTransfer', {'external_device_number': number}));
                $content.find('#input_transfer').on('input', self._onInputNumberDebounced);
                $content.find('#transfer_call').on('click', self._onClickTransferCall);
                return $content;
            }
        });
        $('.o_dial_transfer_button').on('shown.bs.popover', function () {
            $('#input_transfer').focus();
            $('.popover button.btn-close').click(function() {
                $('.o_dial_transfer_button').popover('hide');
             });
        })
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * The call is accepted then we can offer more options to the user.
     */
    activateInCallButtons() {
        this.$('.o_dial_transfer_button').removeAttr('disabled');
        this.$('.o_dial_mute_button').removeAttr('disabled');
    },
    /**
     * Changes the display to show the in call layout.
     */
    hideCallDisplay() {
        this._$phoneCallDetails.removeClass('details_in_call');
        this._$phoneCallDetails.removeClass('details_incoming_call');
        this.$('.o_phonecall_status').hide();
        this._$closeDetails.show();
        this._$phoneCallInfo.show();
        this._$phoneCallInCall.hide();
        this._$phoneCallReceivingCall.hide();
        this.$el.removeClass('in_call');
    },
    /**
     * Changes the display to show the Receiving layout.
     */
    receivingCall() {
        this.$('.o_dial_keypad_button_container').hide();
        this._$phoneCallInCall.hide();
        this._$phoneCallInfoName.hide();
        this._$phoneCallDetails.addClass('details_incoming_call pt-5');

        this._$phoneCallReceivingCall.show();

        this.$('.o_phonecall_top').html(QWeb.render('voip.PhoneCallStatus', {
            status: 'connecting',
        }));
    },
    /**
     * Change message in widget to Ringing
     */
    setStatusRinging() {
        this.$('.o_phonecall_status').html(QWeb.render('voip.PhoneCallStatus', {
             duration: '00:00',
             status: 'ringing',
         }));
     },
    /**
     * Changes the display to show the in call layout.
     */
    showCallDisplay() {
        this._$phoneCallDetails.addClass('details_in_call py-4 bg-success bg-opacity-25');
        this._$closeDetails.hide();
        this._$phoneCallInfo.hide();
        this._$phoneCallInCall.show();
        this._$phoneCallInfoName.show();
        this._$phoneCallActivityButtons.hide();
        this.$el.addClass('in_call');
    },
    /**
     * Starts the timer
     */
    startTimer() {
        this.durationSeconds = 0;
        this._$phoneCallDetails.removeClass('details_incoming_call');
        this._$phoneCallDetails.addClass('details_in_call');
        this._$phoneCallInfoName.hide();

        /**
         * @param {integer} val
         * @return {string}
         */
        function formatTimer(val) {
            return val > 9 ? val : "0" + val;
        }

        setInterval(() => {
            this.durationSeconds++;
            const seconds = formatTimer(this.durationSeconds % 60);
            const minutes = formatTimer(parseInt(this.durationSeconds / 60));
            const duration = _.str.sprintf("%s:%s", minutes, seconds);
            this.$('.o_phonecall_status').html(QWeb.render('voip.PhoneCallStatus', {
                duration,
                status: 'in_call',
            }));
        }, 1000);
    },
    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    async _onClickActivityDone(ev) {
        ev.preventDefault();
        await this._rpc({
            model: 'mail.activity',
            method: 'action_done',
            args: [[this.activityId]],
        });
        Component.env.bus.trigger('voip_reload_chatter');
        this._$phoneCallActivityButtons.hide();
        this.trigger_up('markActivityDone');
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickCallNumber(ev) {
        ev.preventDefault();
        this.trigger_up('clickedOnNumber', {
            number: ev.currentTarget.text,
        });
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    async _onClickCancel(ev) {
        ev.preventDefault();
        await this._rpc({
            model: 'mail.activity',
            method: 'unlink',
            args: [[this.activityId]],
        });
        this._$phoneCallActivityButtons.hide();
        this.trigger_up('cancelActivity');
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickContactLine(ev) {
        $('#input_transfer').val(ev.currentTarget.dataset.number);
    },
    /**
     * @private
     */
    _onClickDetailsClose() {
        $('.o_dial_transfer_button').popover('hide');
        this.trigger_up('closePhonecallDetails');
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickEmail(ev) {
        ev.preventDefault();
        this.trigger_up('fold_panel');
        if (this._activityResModel && this.activityResId) {
            this.do_action({
                context: {
                    default_res_id: this.activityResId,
                    default_composition_mode: 'comment',
                    default_model: this._activityResModel,
                    default_partner_ids: this.partnerId ? [this.partnerId] : [],
                    default_use_template: true,
                },
                key2: 'client_action_multi',
                multi: 'True',
                res_model: 'mail.compose.message',
                src_model: 'voip.phonecall',
                target: 'new',
                type: 'ir.actions.act_window',
                views: [[false, 'form']],
            }, {
                fullscreen: config.device.isMobile
            });
        } else if (this.partnerId) {
            this.do_action({
                context: {
                    default_res_id: this.partnerId,
                    default_composition_mode: 'comment',
                    default_model: 'res.partner',
                    default_partner_ids: [this.partnerId],
                    default_use_template: true,
                },
                key2: 'client_action_multi',
                multi: 'True',
                res_model: 'mail.compose.message',
                src_model: 'voip.phonecall',
                target: 'new',
                type: 'ir.actions.act_window',
                views: [[false, 'form']],
            }, {
                fullscreen: config.device.isMobile
            });
        }
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickLog(ev) {
        ev.preventDefault();
        this.trigger_up('fold_panel');
        this.do_action({
            type: 'ir.actions.act_window',
            res_model: 'mail.activity',
            view_mode: 'form',
            views: [[false, 'form']],
            target: 'new',
            context: {
                default_res_id: this.activityResId,
                default_res_model: this._activityResModel,
            },
            res_id: this.activityId,
        }, {
            fullscreen: config.device.isMobile,
            on_close: () => Component.env.bus.trigger('voip_reload_chatter'),
        });
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickMuteButton(ev) {
        ev.preventDefault();
        if (!this._isMuted) {
            this.trigger_up('muteCall');
            this._$muteIcon.removeClass('fa-microphone');
            this._$muteIcon.addClass('fa-microphone-slash');
            this._isMuted = true;
        } else {
            this.trigger_up('unmuteCall');
            this._$muteIcon.addClass('fa-microphone');
            this._$muteIcon.removeClass('fa-microphone-slash');
            this._isMuted = false;
        }
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickRescheduleActivity(ev) {
        ev.preventDefault();
        this.trigger_up('fold_panel');
        var res_id, res_model;
        if (this.activityResId) {
            res_id = this.activityResId;
            res_model = this._activityResModel;
        } else {
            res_id = this.partnerId;
            res_model = 'res.partner';
        }
        if (res_id) {
            this.do_action({
                type: 'ir.actions.act_window',
                res_model: 'mail.activity',
                view_mode: 'form',
                views: [[false, 'form']],
                target: 'new',
                context: {
                    default_res_id: res_id,
                    default_res_model: res_model,
                },
                res_id: false,
            }, {
                fullscreen: config.device.isMobile
            });
        }
    },
    /**
     * @private
     * @param {MouseEvent} ev
     * @return {Promise}
     */
    async _onClickToPartner(ev) {
        ev.preventDefault();
        this.trigger_up('fold_panel');
        let resId = this.partnerId;
        if (!this.partnerId) {
            let domain = [];
            if (this.phoneNumber && this.mobileNumber) {
                domain = ['|',
                    ['phone', '=', this.phoneNumber],
                    ['mobile', '=', this.mobileNumber]];
            } else if (this.phoneNumber) {
                domain = ['|',
                    ['phone', '=', this.phoneNumber],
                    ['mobile', '=', this.phoneNumber]];
            } else if (this.mobileNumber) {
                domain = [['mobile', '=', this.mobileNumber]];
            }
            const ids = await this._rpc({
                method: 'search_read',
                model: "res.partner",
                kwargs: {
                    domain,
                    fields: ['id'],
                    limit: 1,
                }
            });
            if (ids.length) {
                resId = ids[0].id;
            }
        }
        if (resId !== undefined) {
            this.do_action({
                res_id: resId,
                res_model: "res.partner",
                target: 'new',
                type: 'ir.actions.act_window',
                views: [[false, 'form']],
            }, {
                fullscreen: config.device.isMobile
            });
        } else {
            const context = {};
            if (this.phoneNumber) {
                context.phoneNumber = this.phoneNumber;
            }
            if (this.email) {
                context.email = this.email;
            }
            if (this.mobileNumber) {
                context.mobileNumber = this.mobileNumber;
            }
            this.do_action({
                context,
                res_model: 'res.partner',
                target: 'new',
                type: 'ir.actions.act_window',
                views: [[false, 'form']],
            }, {
                fullscreen: config.device.isMobile
            });
        }
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    async _onClickToRecord(ev) {
        ev.preventDefault();
        const resModel = this._activityResModel;
        const resId = this.activityResId;
        const viewId = await this._rpc({
            model: resModel,
            method: 'get_formview_id',
            args: [[resId]],
            context: session.user_context,
        });
        this.do_action({
            res_id: resId,
            res_model: resModel,
            type: 'ir.actions.act_window',
            views: [[viewId || false, 'form']],
            view_mode: 'form',
            view_type: 'form',
            target: 'new',
        }, {
            fullscreen: config.device.isMobile
        });
    },
    /**
     * @private
     */
    _onClickTransferCall() {
        var number = cleanNumber($('#input_transfer').val());
        if (number && number.length > 0) {
            $('.o_dial_transfer_button').popover('hide');
            core.bus.trigger('transfer_call', number);
        } else {
            $('#input_transfer').addClass('is-invalid')
            $('#input_transfer').focus();
        }
    },
    /**
     * @private
     */
    async _onInputNumber() {
        var self = this;
        var value = $('#input_transfer').val().toLowerCase();
        var number = cleanNumber(value);
        if (number) {
            var domain = ['&', '|',
                ['sanitized_phone', '!=', ''],
                ['sanitized_mobile', '!=', ''],
                '|', '|',
                ['sanitized_phone', 'ilike', number],
                ['sanitized_mobile', 'ilike', number],
                ['name', 'ilike', value],
            ];
        } else {
            var domain = ['&', '|',
                ['sanitized_phone', '!=', ''],
                ['sanitized_mobile', '!=', ''],
                ['name', 'ilike', value],
            ];
        }
        let contacts = await this._rpc({
            model: 'res.partner',
            method: 'search_read',
            domain: [['user_ids', '!=', false]].concat(domain),
            fields: ['id', 'display_name', 'sanitized_phone', 'sanitized_mobile'],
            limit: 8,
        });
        var lines = ''
        for (let i = 0; i < contacts.length; i++) {
            var name = contacts[i].display_name;
            var phone = contacts[i].sanitized_phone;
            var mobile = contacts[i].sanitized_mobile;
            var default_phone = phone;
            var indexOf = name.toLowerCase().indexOf(value);
            var nameBolt = ''
            if (indexOf >= 0) {
                // We matched the name, we made the following line to keep the upper cases
                nameBolt = name.slice(0, indexOf) + '<b>' + name.slice(indexOf, indexOf + value.length) + '</b>' + name.slice(indexOf + value.length)
            } else if (phone && phone.includes(number)) {
                nameBolt = name + ' (' + phone.replace(number, '<b>' + number + '</b>') + ')';
            } else if (mobile && mobile.includes(number)) {
                nameBolt = name + ' (' + mobile.replace(number, '<b>' + number + '</b>') + ')';
                default_phone = mobile;
            }
            lines += '<tr class="transfer_contact_line cursor-pointer" data-number="' + default_phone + '"><td>' + nameBolt + '</td></tr>';
            }
        $('#table_contact').empty().append(lines);
        $('#table_contact tr').on('click', async function(event){self._onClickContactLine(event);});
        $('#input_transfer').removeClass('is-invalid')

        $('.o_dial_transfer_button').popover('update')

    },
});

return PhoneCallDetails;

});
