/** @odoo-module **/

import { AttendeeCalendarModel } from "@calendar/views/attendee_calendar/attendee_calendar_model";
import { patch } from "@web/core/utils/patch";

patch(AttendeeCalendarModel.prototype, "appointment_calendar_model_prototype", {
    /**
     * @override
     */
    setup() {
        this._super(...arguments);
        this.data.slots = {};
        this.slotId = 1;
    },

    processPartialSlotRecord(record) {
        if (!record.end || !record.end.isValid) {
            if (record.isAllDay) {
                record.end = record.start;
            } else {
                record.end = record.start.plus({ minutes: 30 });
            }
        }
        if (!record.isAllDay) {
            record.title = "";
        } else {
            const isSameDay = record.start.hasSame(record.end, "day");
            if (!isSameDay && record.start.hasSame(record.end, "month")) {
                // Simplify date-range if an event occurs into the same month (eg. "August, 4-5 2019")
                record.title = record.start.toFormat("LLLL d") + "-" + record.end.toFormat("d, y");
            } else {
                record.title = isSameDay
                    ? record.start.toFormat("DDD")
                    : record.start.toFormat("DDD") + " - " + record.end.toFormat("DDD");
            }
        }
    },

    createSlot(record) {
        this.processPartialSlotRecord(record);
        const slotId = this.slotId++;
        this.data.slots[slotId] = {
            id: slotId,
            title: record.title,
            start: record.start,
            end: record.end,
            isAllDay: record.isAllDay,
        };
        this.notify();
        return this.data.slots[slotId];
    },

    updateSlot(eventRecord) {
        this.processPartialSlotRecord(eventRecord);
        const slot = this.data.slots[eventRecord.slotId];
        Object.assign(slot, {
            title: eventRecord.title,
            start: eventRecord.start,
            end: eventRecord.end,
            isAllDay: eventRecord.isAllDay,
        });
        this.notify();
    },

    removeSlot(slotId) {
        delete this.data.slots[slotId];
        this.notify();
    },

    clearSlots() {
        this.data.slots = {};
        this.notify();
    },
});
