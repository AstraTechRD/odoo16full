/** @odoo-module **/

import { AttendeeCalendarCommonRenderer } from "@calendar/views/attendee_calendar/common/attendee_calendar_common_renderer";
import { patch } from "@web/core/utils/patch";
import { useAppointmentRendererHook } from "@appointment/views/appointment_calendar/hooks";

patch(AttendeeCalendarCommonRenderer.prototype, "appointment_calendar_common_renderer", {
    setup() {
        this._super(...arguments);
        const fns = useAppointmentRendererHook(
            () => [this.fc.el],
        );
        Object.assign(this, fns);
    },

    get options() {
        const options = this._super();
        if (this.getEventTimeFormat) {
            options.eventTimeFormat = this.getEventTimeFormat();
        }
        options.eventAllow = this.onEventAllow;
        return options;
    },

    /**
     * @override
     */
    mapRecordsToEvents() {
        this.maxResId = Math.max(Object.keys(this.props.model.data.records).map((id) => Number.parseInt(id)));
        const res = [
            ...this._super(...arguments),
            ...Object.values(this.props.model.data.slots).map((r) => this.convertSlotToEvent(r)),
        ];
        return res;
    },

    /**
     * @override
     */
    convertSlotToEvent(record) {
        const result = {
            ...this.convertRecordToEvent(record),
            id: this.maxResId + record.id, // Arbitrary id to avoid duplicated ids.
            slotId: record.id,
            color: "green",
        };
        return result;
    },

    /**
     * @override
     */
    fcEventToRecord(event) {
        if (!event.extendedProps || !event.extendedProps.slotId) {
            return this._super(...arguments);
        }
        return {
            ...this._super({
                allDay: event.allDay,
                date: event.date,
                start: event.start,
                end: event.end,
            }),
            slotId: event.extendedProps.slotId,
        };
    },

    /**
     * @overrde
     */
    onEventClick(info) {
        if (!this.isSlotCreationMode()) {
            return this._super(...arguments);
        }
        info.jsEvent.preventDefault();
        info.jsEvent.stopPropagation();
        if (info.event.extendedProps.slotId) {
            info.event.remove();
            this.props.model.removeSlot(info.event.extendedProps.slotId);
        }
    },

    /**
     * @override
     */
    onEventRender(info) {
        this._super(...arguments);
        const { el, event } = info;
        if (event.extendedProps.slotId) {
            el.classList.add("o_calendar_slot");
            const bg = el.querySelector(".fc-bg");
            if (bg) {
                const duration = (event.end - event.start) / 3600000;
                const iconSize = duration < 1 || event.allDay || this.props.model.scale === "month" ? "" : "h1";
                const domParser = new DOMParser();
                const injectedContentEl = domParser.parseFromString(
                    /* xml */ `
                    <button class="close border-0 p-0 m-0 w-100 h-100 disabled o_hidden">
                        <i class='fa fa-trash text-white m-0 ${iconSize}'></i>
                    </button>
                `,
                    "text/html"
                ).body.firstChild;
                bg.appendChild(injectedContentEl);
            }
        }
    },

    /**
     * @override
     */
    isSelectionAllowed(event) {
        let result = this._super(...arguments);
        if (this.isSlotCreationMode()) {
            result = result && luxon.DateTime.fromJSDate(event.start) > luxon.DateTime.now();
        }
        return result;
    },

    /**
     * @override
     */
    async onSelect(info) {
        if (!this.isSlotCreationMode()) {
            return this._super(...arguments);
        }
        this.props.model.createSlot(this.fcEventToRecord(info));
        this.fc.api.unselect();
    },

    /**
     * @override
     */
    onDateClick(info) {
        if (!this.isSlotCreationMode()) {
            return this._super(...arguments);
        }
        // Disabled in month view
        if (this.props.model.scale === "month") {
            return;
        }
        const date = luxon.DateTime.fromISO(info.dateStr);
        if (date < luxon.DateTime.now()) {
            return;
        }
        this.props.model.createSlot(this.fcEventToRecord(info));
    },

    /**
     * @override
     */
    onEventDrop(info) {
        if (!this.isSlotCreationMode()) {
            return this._super(...arguments);
        }
        this.props.model.updateSlot(this.fcEventToRecord(info.event));
    },

    /**
     * @override
     */
    onEventResize(info) {
        if (!this.isSlotCreationMode()) {
            return this._super(...arguments);
        }
        this.props.model.updateSlot(this.fcEventToRecord(info.event));
    },

    /**
     * @override
     */
    onEventDragStart(info) {
        if (!this.isSlotCreationMode()) {
            return this._super(...arguments);
        }
    },

    /**
     * @override
     */
    onEventResizeStart(info) {
        if (!this.isSlotCreationMode()) {
            return this._super(...arguments);
        }
    },

    /**
     * @override
     */
    onEventMouseEnter(info) {
        if (!this.isSlotCreationMode()) {
            return this._super(...arguments);
        }
        const buttonEl = info.el.querySelector(".fc-bg > button");
        buttonEl && buttonEl.classList.remove("o_hidden");
    },

    /**
     * @override
     */
    onEventMouseLeave(info) {
        if (!this.isSlotCreationMode()) {
            return this._super(...arguments);
        }
        const buttonEl = info.el.querySelector(".fc-bg > button");
        buttonEl && buttonEl.classList.add("o_hidden");
    },

    /**
     * Prevent drag & drop events in the past in slot creationmode
     */
    onEventAllow(dropInfo, draggedEvent) {
        if (!this.isSlotCreationMode()) {
            return (this._super && this._super(...arguments)) || true;
        }
        return draggedEvent.extendedProps.slotId && luxon.DateTime.fromJSDate(dropInfo.start) > luxon.DateTime.now();
    },
});
