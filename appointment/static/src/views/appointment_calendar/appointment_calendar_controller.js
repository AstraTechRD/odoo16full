/** @odoo-module **/

import { AttendeeCalendarController } from "@calendar/views/attendee_calendar/attendee_calendar_controller";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { Tooltip } from "@web/core/tooltip/tooltip";
import { browser } from "@web/core/browser/browser";
import { serializeDateTime } from "@web/core/l10n/dates";

const { useRef, useState, useSubEnv, onWillStart } = owl;

patch(AttendeeCalendarController.prototype, "appointment_calendar_controller", {
    setup() {
        this._super(...arguments);
        this.rpc = useService("rpc");
        this.popover = useService("popover");
        this.copyLinkRef = useRef("copyLinkRef");

        this.appointmentState = useState({
            data: {},
            lastAppointmentUrl: false,
        });

        useSubEnv({
            calendarState: useState({
                mode: "default",
            }),
        });

        onWillStart(async () => {
            this.appointmentState.data = await this.rpc(
                "/appointment/appointment_type/get_staff_user_appointment_types"
            );
        });
    },

    /**
     * Returns whether we have slot events.
     */
    hasSlotEvents() {
        return Object.keys(this.model.data.slots).length;
    },

    _writeUrlToClipboard() {
        if (!this.appointmentState.lastAppointmentUrl) {
            return;
        }
        navigator.clipboard.writeText(this.appointmentState.lastAppointmentUrl);
    },

    onClickSelectAvailabilities() {
        this.env.calendarState.mode = "slots-creation";
    },

    async onClickGetShareLink() {
        if (!this.appointmentState.lastAppointmentUrl) {
            const slots = Object.values(this.model.data.slots).map(slot => ({
                start: serializeDateTime(slot.start),
                end: serializeDateTime(slot.start === slot.end ? slot.end.plus({ days: 1 }) : slot.end), //TODO: check if necessary
                allday: slot.isAllDay,
            }));
            const customAppointment = await this.rpc(
                "/appointment/appointment_type/create_custom",
                {
                    slots: slots,
                    context: this.props.context,
                },
            );
            if (customAppointment.appointment_type_id) {
                this.appointmentState.lastAppointmentUrl = customAppointment.invite_url;
            }
            this.env.calendarState.mode = "default";
            this.model.clearSlots();
        }
        this._writeUrlToClipboard();
        if (!this.copyLinkRef.el) {
            return;
        }
        const closeTooltip = this.popover.add(this.copyLinkRef.el, Tooltip, {
            tooltip: this.env._t("Copied !"),
        }, {
            position: "left",
        });
        browser.setTimeout(() => {
            closeTooltip();
        }, 800);
    },

    onClickDiscard() {
        if (this.env.calendarState.mode === "slots-creation") {
            this.model.clearSlots();
        }
        this.env.calendarState.mode = "default";
        this.appointmentState.lastAppointmentUrl = undefined;
    },

    async onClickSearchCreateAnytimeAppointment() {
        const anytimeAppointment = await this.rpc("/appointment/appointment_type/search_create_anytime");
        if (anytimeAppointment.appointment_type_id) {
            this.appointmentState.lastAppointmentUrl = anytimeAppointment.invite_url;
            this._writeUrlToClipboard();
        }
    },

    async onClickGetAppointmentUrl(appointmentTypeId) {
        const appointment = await this.rpc("/appointment/appointment_type/get_book_url", {
            appointment_type_id: appointmentTypeId,
        });
        this.appointmentState.lastAppointmentUrl = appointment.invite_url;
        this._writeUrlToClipboard();
    },
});
