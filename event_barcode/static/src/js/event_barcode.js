odoo.define('event_barcode.EventScanView', function (require) {
"use strict";

var AbstractAction = require('web.AbstractAction');
var core = require('web.core');
var Dialog = require('web.Dialog');

var _t = core._t;
var QWeb = core.qweb;


// load widget with main barcode scanning View
var EventScanView = AbstractAction.extend({
    contentTemplate: 'event_barcode_template',
    events: {
        'click .o_event_select_attendee': '_onClickSelectAttendee',
        'click .o_event_previous_menu': '_onClickBackToEvents',
    },

    /**
     * @override
     */
    init: function(parent, action) {
        this._super.apply(this, arguments);
        this.eventId = action.context.default_event_id || (action.context.active_model === 'event.event' && action.context.active_id);
        this.isMultiEvent = ! this.eventId;
    },

    /**
     * @override
     * Fetch barcode init information. Notably eventId triggers mono- or multi-
     * event mode (Registration Desk in multi event allow to manage attendees
     * from several events and tickets without reloading / changing event in UX.
     */
    willStart: function() {
        var self = this;
        return this._super().then(async function() {
            self.data = await self._rpc({
                route: '/event/init_barcode_interface',
                params: {
                    event_id: self.eventId,
                }
            });
        });

    },

    /**
     * @override
     */
    start: function() {
        core.bus.on('barcode_scanned', this, this._onBarcodeScanned);
    },

    /**
     * @override
     */
    destroy: function () {
        core.bus.off('barcode_scanned', this, this._onBarcodeScanned);
        this._super();
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {string} barcode
     *
     * When scanning a barcode, call Registration.register_attendee() to get
     * formatted registration information, notably its status or event-related
     * information. Open a confirmation / choice Dialog to confirm attendee.
     */
    _onBarcodeScanned: function(barcode) {
        var self = this;
        this._rpc({
            model: 'event.registration',
            method: 'register_attendee',
            kwargs: {
                barcode: barcode,
                event_id: this.eventId,
            }
        }).then(function(result) {
            if (result.error && result.error === 'invalid_ticket') {
                self.displayNotification({ title: _t("Warning"), message: _t('Invalid ticket'), type: 'danger' });
            } else {
                self.registrationId = result.id;
                new Dialog(self, self._getSummaryModalConfig(result)).open();
            }
        });
    },

    /**
     * @private
     */
    _onClickSelectAttendee: function() {
        if (this.isMultiEvent) {
            this.do_action("event.event_registration_action");
        } else {
            this.do_action("event.event_registration_action_kanban", {
                additional_context: {
                    active_id: this.eventId,
                    search_default_unconfirmed: true,
                    search_default_confirmed: true,
                }
            });
        }
    },

    /**
     * @private
     * @param {Event} ev
     */
    _onClickBackToEvents: function(ev) {
        ev.preventDefault();
        if (this.isMultiEvent) {
            // define action from scratch instead of using existing 'action_event_view' to avoid
            // messing with menu bar
            this.do_action({
                type: 'ir.actions.act_window',
                name: _t('Events'),
                res_model: 'event.event',
                views: [
                    [false, 'kanban'],
                    [false, 'calendar'],
                    [false, 'list'],
                    [false, 'gantt'],
                    [false, 'form'],
                    [false, 'pivot'],
                    [false, 'graph'],
                    [false, 'map'],
                ],
                target:'main'
            });
        } else {
            return this.do_action({
                type: 'ir.actions.act_window',
                res_model: 'event.event',
                res_id: this.eventId,
                views: [[false, 'form']],
                target:'main'
            });
        }
    },

    /**
     * @private
     */
    _onRegistrationConfirm: function() {
        var self = this;
        this._rpc({
            model: 'event.registration',
            method: 'action_set_done',
            args: [this.registrationId]
        }).then(function () {
            self.displayNotification({ message: _t("Registration confirmed") });
        });
    },

    /**
     * @private
     */
    _onRegistrationPrintPdf: function() {
        this.do_action({
            type: 'ir.actions.report',
            report_type: 'qweb-pdf',
            report_name: `event.event_registration_report_template_foldable_badge/${this.registrationId}`,
        });
    },

    /**
     * @private
     */
    _onRegistrationView: function() {
        this.do_action({
            type: 'ir.actions.act_window',
            res_model: 'event.registration',
            res_id: this.registrationId,
            views: [[false, 'form']],
            target: 'current'
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {object} registration: result from Registration.register_attendee()
     */
    _getSummaryModalConfig: function(registration) {
        return {
            title: _t('Registration Summary'),
            size: 'medium',
            $content: QWeb.render('event_registration_summary', {'registration': registration}),
            buttons: this._getSummaryModalConfigButtons(registration.status),
        };
    },

    /**
     * @private
     * @param {string} registration_status: status of registration, see result
     *   from Registration.register_attendee()
     */
    _getSummaryModalConfigButtons: function(registration_status) {
        var self = this;
        var buttons = [];
        if (registration_status === 'need_manual_confirmation') {
            buttons.push({
                text: _t('Confirm'),
                close: true,
                classes: 'btn-primary',
                click: function() {
                    self._onRegistrationConfirm();
                }
            }, {
                text: _t('Close'),
                close: true,
                classes: 'btn-secondary'
            });
        } else {
            buttons.push({text: _t('Close'), close: true, classes: 'btn-primary'});
        }
        buttons.push({
            text: _t('Print'),
            click: function () {
                self._onRegistrationPrintPdf();
            }
        }, {
            text: _t('View'),
            close: true,
            click: function() {
                self._onRegistrationView();
            }
        });
        return buttons;
    },
});

core.action_registry.add('even_barcode.event_barcode_scan_view', EventScanView);

return EventScanView;

});
