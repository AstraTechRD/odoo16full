/** @odoo-module **/

import { click, nextTick, getFixture, patchDate, patchWithCleanup } from "@web/../tests/helpers/utils";
import { clickAllDaySlot } from "@web/../tests/views/calendar/helpers";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { registry } from "@web/core/registry";
import { userService } from "@web/core/user_service";
import testUtils from 'web.test_utils';

const serviceRegistry = registry.category("services");

let target;
let serverData;
const uid = 1;

QUnit.module('appointment.appointment_link', {
    beforeEach: function () {
        serverData = {
            models: {
                'res.users': {
                    fields: {
                        id: {string: 'ID', type: 'integer'},
                        name: {string: 'Name', type: 'char'},
                        partner_id: {string: 'Partner', type: 'many2one', relation: 'res.partner'},
                    },
                    records: [
                        {id: uid, name: 'User 1', partner_id: 1},
                        {id: 214, name: 'User 214', partner_id: 214},
                        {id: 216, name: 'User 216', partner_id: 216},
                    ],
                },
                'res.partner': {
                    fields: {
                        id: {string: 'ID', type: 'integer'},
                        display_name: {string: "Displayed name", type: "char"},
                    },
                    records: [
                        {id: 1, display_name: 'Partner 1'},
                        {id: 214, display_name: 'Partner 214'},
                        {id: 216, display_name: 'Partner 216'},
                    ],
                },
                'calendar.event': {
                    fields: {
                        id: {string: 'ID', type: 'integer'},
                        user_id: {string: 'User', type: 'many2one', relation: 'res.users'},
                        partner_id: {string: 'Partner', type: 'many2one', relation: 'res.partner', related: 'user_id.partner_id'},
                        name: {string: 'Name', type: 'char'},
                        start_date: {string: 'Start date', type: 'date'},
                        stop_date: {string: 'Stop date', type: 'date'},
                        start: {string: 'Start datetime', type: 'datetime'},
                        stop: {string: 'Stop datetime', type: 'datetime'},
                        allday: {string: 'Allday', type: 'boolean'},
                        partner_ids: {string: 'Attendees', type: 'one2many', relation: 'res.partner'},
                        appointment_type_id: {string: 'Appointment Type', type: 'many2one', relation: 'appointment.type'},
                    },
                    records: [{
                        id: 1,
                        user_id: uid,
                        partner_id: uid,
                        name: 'Event 1',
                        start: moment().add(1, 'years').format('YYYY-01-12 10:00:00'),
                        stop: moment().add(1, 'years').format('YYYY-01-12 11:00:00'),
                        allday: false,
                        partner_ids: [1],
                    }, {
                        id: 2,
                        user_id: uid,
                        partner_id: uid,
                        name: 'Event 2',
                        start: moment().add(1, 'years').format('YYYY-01-05 10:00:00'),
                        stop: moment().add(1, 'years').format('YYYY-01-05 11:00:00'),
                        allday: false,
                        partner_ids: [1],
                    }, {
                        id: 3,
                        user_id: 214,
                        partner_id: 214,
                        name: 'Event 3',
                        start: moment().add(1, 'years').format('YYYY-01-05 10:00:00'),
                        stop: moment().add(1, 'years').format('YYYY-01-05 11:00:00'),
                        allday: false,
                        partner_ids: [214],
                    }
                    ],
                    check_access_rights: function () {
                        return Promise.resolve(true);
                    }
                },
                'appointment.type': {
                    fields: {
                        name: {type: 'char'},
                        website_url: {type: 'char'},
                        staff_user_ids: {type: 'many2many', relation: 'res.users'},
                        website_published: {type: 'boolean'},
                        slot_ids: {type: 'one2many', relation: 'appointment.slot'},
                        category: {
                            type: 'selection',
                            selection: [['website', 'Website'], ['custom', 'Custom']]
                        },
                    },
                    records: [{
                        id: 1,
                        name: 'Very Interesting Meeting',
                        website_url: '/appointment/1',
                        website_published: true,
                        staff_user_ids: [214],
                        category: 'website',
                    }, {
                        id: 2,
                        name: 'Test Appointment',
                        website_url: '/appointment/2',
                        website_published: true,
                        staff_user_ids: [uid],
                        category: 'website',
                    }],
                },
                'appointment.slot': {
                    fields: {
                        appointment_type_id: {type: 'many2one', relation: 'appointment.type'},
                        start_datetime: {string: 'Start', type: 'datetime'},
                        end_datetime: {string: 'End', type: 'datetime'},
                        duration: {string: 'Duration', type: 'float'},
                        slot_type: {
                            string: 'Slot Type',
                            type: 'selection',
                            selection: [['recurring', 'Recurring'], ['unique', 'One Shot']],
                        },
                    },
                },
                'filter_partner': {
                    fields: {
                        id: {string: "ID", type: "integer"},
                        user_id: {string: "user", type: "many2one", relation: 'res.users'},
                        partner_id: {string: "partner", type: "many2one", relation: 'res.partner'},
                        partner_checked: {string: "checked", type: "boolean"},
                    },
                    records: [
                        {
                            id: 4,
                            user_id: uid,
                            partner_id: uid,
                            partner_checked: true
                        }, {
                            id: 5,
                            user_id: 214,
                            partner_id: 214,
                            partner_checked: true,
                        }
                    ]
                },
            },
            views: {},
        };
        patchDate(moment().add(1, 'years').year(), 0, 5, 0, 0, 0);
        target = getFixture();
        setupViewRegistries();
        serviceRegistry.add(
            "user",
            {
                ...userService,
                start() {
                    const fakeUserService = userService.start(...arguments);
                    Object.defineProperty(fakeUserService, "userId", {
                        get: () => uid,
                    });
                    return fakeUserService;
                },
            },
            { force: true }
        );
    },
}, function () {

QUnit.test('verify appointment links button are displayed', async function (assert) {
    assert.expect(3);

    await makeView({
        type: "calendar",
        resModel: 'calendar.event',
        serverData,
        arch: 
        `<calendar class="o_calendar_test"
                    js_class="attendee_calendar"
                    all_day="allday"
                    date_start="start"
                    date_stop="stop"
                    attendee="partner_ids">
            <field name="name"/>
            <field name="partner_ids" write_model="filter_partner" write_field="partner_id"/>
            <field name="partner_id" filters="1" invisible="1"/>
        </calendar>`,
        mockRPC: async function (route, args) {
            if (route === '/web/dataset/call_kw/res.partner/get_attendee_detail') {
                return Promise.resolve([]);
            }
        },
    });

    assert.containsOnce(target, 'button:contains("Share Availabilities")');

    await click(target, '#dropdownAppointmentLink');

    assert.containsOnce(target, 'button:contains("Test Appointment")');

    assert.containsOnce(target, 'button:contains("Any Time")');
});

QUnit.test('create/search anytime appointment type', async function (assert) {
    assert.expect(9);

    patchWithCleanup(navigator, {
        clipboard: {
            writeText: (value) => {
                assert.strictEqual(
                    value,
                    `http://amazing.odoo.com/appointment/3?filter_staff_user_ids=%5B${uid}%5D`
                );
            }
        },
    });

    await makeView({
        type: "calendar",
        resModel: 'calendar.event',
        serverData,
        arch:
        `<calendar class="o_calendar_test"
                    js_class="attendee_calendar"
                    all_day="allday"
                    date_start="start"
                    date_stop="stop"
                    color="partner_id">
            <field name="name"/>
            <field name="partner_ids" write_model="filter_partner" write_field="partner_id"/>
        </calendar>`,
        mockRPC: function (route, args) {
            if (route === "/appointment/appointment_type/search_create_anytime") {
                assert.step(route);
            } else if (route === '/web/dataset/call_kw/res.partner/get_attendee_detail') {
                return Promise.resolve([]);
            }
        },
        session: {
            'web.base.url': 'http://amazing.odoo.com',
        },
    });

    assert.strictEqual(2, serverData.models['appointment.type'].records.length)

    await click(target.querySelector('#dropdownAppointmentLink'));

    await click(target.querySelector('.o_appointment_search_create_anytime_appointment'));
    await nextTick();

    assert.verifySteps(['/appointment/appointment_type/search_create_anytime']);
    assert.strictEqual(3, serverData.models['appointment.type'].records.length,
        "Create a new appointment type")

    await click(target.querySelector('.o_appointment_discard_slots'));
    await click(target.querySelector('#dropdownAppointmentLink'));

    await click(target.querySelector('.o_appointment_search_create_anytime_appointment'));
    await nextTick();

    assert.verifySteps(['/appointment/appointment_type/search_create_anytime']);
    assert.strictEqual(3, serverData.models['appointment.type'].records.length,
        "Does not create a new appointment type");
});

QUnit.test('discard slot in calendar', async function (assert) {
    assert.expect(11);

    const calendar = await makeView({
        type: "calendar",
        resModel: 'calendar.event',
        serverData,
        arch:
        `<calendar class="o_calendar_test"
                    js_class="attendee_calendar"
                    all_day="allday"
                    date_start="start"
                    date_stop="stop">
            <field name="name"/>
            <field name="partner_ids" write_model="filter_partner" write_field="partner_id"/>
        </calendar>`,
        mockRPC: async function (route, args) {
            if (route === '/web/dataset/call_kw/res.partner/get_attendee_detail') {
                return Promise.resolve([]);
            }
        },
    });

    await click(target.querySelector('.o_calendar_filter_item[data-value=all] input'));
    await click(target.querySelector('.o_appointment_select_slots'));
    await nextTick();

    assert.strictEqual(calendar.env.calendarState.mode, 'slots-creation',
        "The calendar is now in a mode to create custom appointment time slots");
    assert.containsN(target, '.fc-event', 2);
    assert.containsNone(target, '.o_calendar_slot');
    
    await click(target.querySelector('.o_calendar_button_next'));
    assert.containsOnce(target, '.fc-event', 'There is one calendar event');
    assert.containsNone(target, '.o_calendar_slot', 'There is no slot yet');

    await clickAllDaySlot(target, moment().format('YYYY-01-12'));
    await nextTick();
    assert.containsN(target, '.fc-event', 2, 'There is 2 events in the calendar');
    assert.containsOnce(target, '.o_calendar_slot', 'One of them is a slot');

    await click(target.querySelector('button.o_appointment_discard_slots'));
    await nextTick();
    assert.containsOnce(target, '.fc-event', 'The calendar event is still here');
    assert.containsNone(target, '.o_calendar_slot', 'The slot has been discarded');

    await click(target.querySelector('.o_calendar_button_prev'));
    assert.containsN(target, '.fc-event', 2);
    assert.containsNone(target, '.o_calendar_slot');
});

QUnit.test("cannot move real event in slots-creation mode", async function (assert) {
    assert.expect(4);

    const calendar = await makeView({
        type: "calendar",
        resModel: 'calendar.event',
        serverData,
        arch: 
        `<calendar class="o_calendar_test"
                    js_class="attendee_calendar"
                    all_day="allday"
                    date_start="start"
                    date_stop="stop">
            <field name="name"/>
            <field name="start"/>
            <field name="partner_ids" write_model="filter_partner" write_field="partner_id"/>
        </calendar>`,
        mockRPC: function (route, args) {
            if (args.method === "write") {
                assert.step('write event');
            } else if (route === '/web/dataset/call_kw/res.partner/get_attendee_detail') {
                return Promise.resolve([]);
            }
        },
    });

    await click(target.querySelector('.o_calendar_filter_item[data-value=all] input'));
    await click(target.querySelector('.o_appointment_select_slots'));

    assert.strictEqual(calendar.env.calendarState.mode, 'slots-creation',
        "The calendar is now in a mode to create custom appointment time slots");
    assert.containsN(target, '.fc-event', 2);
    assert.containsNone(target, '.o_calendar_slot');

    await testUtils.dom.dragAndDrop($(target.querySelector('.fc-event')), $(target.querySelector('.fc-day')));
    await nextTick();

    assert.verifySteps([]);
});

QUnit.test("create slots for custom appointment type", async function (assert) {
    assert.expect(13);

    patchWithCleanup(navigator, {
        clipboard: {
            writeText: (value) => {
                assert.strictEqual(
                    value,
                    `http://amazing.odoo.com/appointment/3?filter_staff_user_ids=%5B${uid}%5D`
                );
            }
        }
    });

    const calendar = await makeView({
        type: "calendar",
        resModel: 'calendar.event',
        serverData,
        arch: 
        `<calendar class="o_calendar_test"
                    js_class="attendee_calendar"
                    all_day="allday"
                    date_start="start"
                    date_stop="stop">
            <field name="name"/>
            <field name="partner_ids" write_model="filter_partner" write_field="partner_id"/>
        </calendar>`,
        mockRPC: function (route, args) {
            if (route === "/appointment/appointment_type/create_custom") {
                assert.step(route);
            } else if (route === '/web/dataset/call_kw/res.partner/get_attendee_detail') {
                return Promise.resolve([]);
            }
        },
    });

    await click(target.querySelector('.o_calendar_filter_item[data-value=all] input'));
    await click(target.querySelector('.o_appointment_select_slots'));

    assert.strictEqual(calendar.env.calendarState.mode, 'slots-creation',
        "The calendar is now in a mode to create custom appointment time slots");
    assert.containsN(target, '.fc-event', 2);
    assert.containsNone(target, '.o_calendar_slot');
    
    await click(target.querySelector('.o_calendar_button_next'));
    assert.containsOnce(target, '.fc-event', 'There is one calendar event');
    assert.containsNone(target, '.o_calendar_slot', 'There is no slot yet');

    await clickAllDaySlot(target, moment().format('YYYY-01-12'));
    await nextTick();
    assert.containsN(target, '.fc-event', 2, 'There is 2 events in the calendar');
    assert.containsOnce(target, '.o_calendar_slot', 'One of them is a slot');

    await click(target.querySelector('button.o_appointment_get_link'));
    assert.verifySteps(['/appointment/appointment_type/create_custom']);
    assert.containsOnce(target, '.fc-event', 'The calendar event is still here');
    assert.containsNone(target, '.o_calendar_slot', 'The slot has been cleared after the creation');
    assert.strictEqual(serverData.models['appointment.slot'].records.length, 1);
});

QUnit.test('filter works in slots-creation mode', async function (assert) {
    assert.expect(11);

    const calendar = await makeView({
        type: "calendar",
        resModel: 'calendar.event',
        serverData,
        arch: 
        `<calendar class="o_calendar_test"
                    js_class="attendee_calendar"
                    all_day="allday"
                    date_start="start"
                    date_stop="stop"
                    color="partner_id">
            <field name="name"/>
            <field name="partner_ids" write_model="filter_partner" write_field="partner_id"/>
            <field name="partner_id" filters="1" invisible="1"/>
        </calendar>`,
        mockRPC: function (route, args) {
            if (route === '/web/dataset/call_kw/res.partner/get_attendee_detail') {
                return Promise.resolve([]);
            }
        },
    });

    await click(target.querySelector('.o_calendar_filter_item[data-value=all] input'));
    // Two events are displayed
    assert.containsN(target, '.fc-event', 2);
    assert.containsNone(target, '.o_calendar_slot');

    // Switch to slot-creation mode and create a slot for a custom appointment type
    await click(target.querySelector('.o_appointment_select_slots'));

    assert.strictEqual(calendar.env.calendarState.mode, 'slots-creation',
        "The calendar is now in a mode to create custom appointment time slots");

    await click(target.querySelector('.o_calendar_button_next'));
    assert.containsOnce(target, '.fc-event');
    assert.containsNone(target, '.o_calendar_slot');

    await clickAllDaySlot(target, moment().format('YYYY-01-12'));
    await nextTick();
    assert.containsN(target, '.fc-event', 2, 'There is 2 events in the calendar');
    assert.containsOnce(target, '.o_calendar_slot', 'One of them is a slot');

    // Modify filters of the calendar to display less calendar event
    await click(target.querySelector('.o_calendar_filter_item:last-of-type > input'));
    assert.containsOnce(target, '.fc-event', 'There is now only 1 events displayed');
    assert.containsOnce(target, '.o_calendar_slot', 'The slot created is still displayed');

    await click(target.querySelector('.o_calendar_filter_item:last-of-type > input'));
    await click(target.querySelector('button.o_appointment_discard_slots'));
    assert.containsOnce(target, '.fc-event', 'There is now only 1 calendar event displayed');
    assert.containsNone(target, '.o_calendar_slot', 'There is no more slots in the calendar view');
});

QUnit.test('click & copy appointment type url', async function (assert) {
    assert.expect(3);

    patchWithCleanup(navigator, {
        clipboard: {
            writeText: (value) => {
                assert.strictEqual(
                    value,
                    `http://amazing.odoo.com/appointment/2?filter_staff_user_ids=%5B${uid}%5D`
                );
            }
        }
    });

    await makeView({
        type: "calendar",
        resModel: 'calendar.event',
        serverData,
        arch: 
        `<calendar class="o_calendar_test"
                    js_class="attendee_calendar"
                    all_day="allday"
                    date_start="start"
                    date_stop="stop"
                    color="partner_id">
            <field name="name"/>
            <field name="partner_ids" write_model="filter_partner" write_field="partner_id"/>
        </calendar>`,
        mockRPC: function (route, args) {
            if (route === '/appointment/appointment_type/get_book_url') {
                assert.step(route)
            } else if (route === '/web/dataset/call_kw/res.partner/get_attendee_detail') {
                return Promise.resolve([]);
            }
        },
    });

    await click(target.querySelector('#dropdownAppointmentLink'));
    await click(target.querySelector('.o_appointment_appointment_link_clipboard'));

    assert.verifySteps(['/appointment/appointment_type/get_book_url']);
});
});
