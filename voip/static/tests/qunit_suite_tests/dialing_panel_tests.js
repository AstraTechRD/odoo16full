/** @odoo-module **/

import { start } from '@mail/../tests/helpers/test_utils';

import DialingPanel from 'voip.DialingPanel';
import UserAgent from 'voip.UserAgent';

import mobile from 'web_mobile.core';

import core from 'web.core';
import { registry } from '@web/core/registry';
import { ComponentAdapter } from "web.OwlCompatibility";
import testUtils from 'web.test_utils';

class DialingPanelComponent extends ComponentAdapter {
    setup() {
        super.setup(...arguments);
        this.env = owl.Component.env;
    }
}

/**
 * Create a dialing Panel. Params are used to create the underlying web client.
 *
 * @param {Object} params
 * @returns {Object} The value returned by the start method.
 */
async function createDialingPanel(params) {
    registry.category('main_components').add('DialingPanel', {
        Component: DialingPanelComponent,
        props: {
            Component: DialingPanel,
        }
    });
    const result = await start({
        ...params,
    });
    core.bus.trigger('voip_onToggleDisplay');
    await testUtils.nextTick();
    return result;
}

QUnit.module('voip', {}, function () {
QUnit.module('DialingPanel', {
    beforeEach() {
        this.onaccepted = undefined;
        this.recentList = {};
        this.mockPhoneCallDetails = id => {
            return {
                activity_id: 50+id,
                activity_model_name: "A model",
                activity_note: false,
                activity_res_id: 200+id,
                activity_res_model: 'res.model',
                activity_summary: false,
                date_deadline: "2018-10-26",
                id,
                mobile: false,
                name: `Record ${id}`,
                note: false,
                partner_email: `partner ${100+id} @example.com`,
                partner_id: 100+id,
                partner_avatar_128: '',
                partner_name: `Partner ${100+id}`,
                phone: "(215)-379-4865",
                state: 'open',
            }
        };
        // generate 3 records
        this.phoneCallDetailsData = [10,23,42].map(id => {
            return this.mockPhoneCallDetails(id);
        });
        testUtils.mock.patch(UserAgent, {
            /**
             * Register callback to avoid the timeout that will accept the call
             * after 3 seconds in demo mode
             *
             * @override
             * @private
             * @param {function} func
             */
            _demoTimeout: func => {
                this.onaccepted = func;
            }
        });

        const mockServerRegistry = registry.category('mock_server');
        if (!mockServerRegistry.contains('get_missed_call_info')) {
            mockServerRegistry.add('get_missed_call_info', () => []);
        }
        if (!mockServerRegistry.contains('hangup_call')) {
            mockServerRegistry.add('hangup_call', () => []);
        }
        if (!mockServerRegistry.contains('get_recent_list')) {
            mockServerRegistry.add('get_recent_list', () => []);
        }
    },
    afterEach() {
        testUtils.mock.unpatch(UserAgent);
    },
}, function () {

QUnit.test('autocall flow', async function (assert) {
    assert.expect(35);

    const self = this;
    let counterNextActivities = 0;

    const { messaging } = await createDialingPanel({
        async mockRPC(route, args) {
            if (args.method === 'get_pbx_config') {
                return { mode: 'demo' };
            }
            if (args.model === 'voip.phonecall') {
                const id = args.args[0];
                switch (args.method) {
                case 'get_next_activities_list':
                    counterNextActivities++;
                    return self.phoneCallDetailsData.filter(phoneCallDetailData =>
                        ['done', 'cancel'].indexOf(phoneCallDetailData.state) === -1);
                case 'get_recent_list':
                    return self.phoneCallDetailsData.filter(phoneCallDetailData =>
                        phoneCallDetailData.state === 'open');
                case 'init_call':
                    assert.step('init_call');
                    return [];
                case 'hangup_call':
                    if (args.kwargs.done) {
                        self.phoneCallDetailsData.find(d => d.id === id).state = 'done';
                    }
                    assert.step('hangup_call');
                    return;
                case 'create_from_rejected_call':
                    (self.phoneCallDetailsData.find(d => d.id === id) || {}).state = 'pending';
                    assert.step('rejected_call');
                    return {id: 418};
                case 'canceled_call':
                    self.phoneCallDetailsData.find(d => d.id === id).state = 'pending';
                    assert.step('canceled_call');
                    return [];
                case 'remove_from_queue':
                    self.phoneCallDetailsData.find(d => d.id === id).state = 'cancel';
                    assert.step('remove_from_queue');
                    return [];
                case 'create_from_incoming_call':
                    assert.step('incoming_call');
                    return {id: 200};
                case 'create_from_incoming_call_accepted':
                    assert.step('incoming_call_accepted');
                    self.phoneCallDetailsData.push(self.mockPhoneCallDetails(201));
                    return {id: 201};
                }
            }
        },
    });

    // make a first call
    assert.containsNone(
        document.body,
        '.o_phonecall_details',
        "Details should not be visible yet");
    assert.containsN(
        document.body, `
            .o_dial_next_activities
            .o_dial_phonecalls
            .o_dial_phonecall`,
        3,
        "Next activities tab should have 3 phonecalls at the beginning");

    // select first call with autocall
    await testUtils.dom.click(document.querySelector('.o_dial_call_button'));
    assert.isVisible(
        document.querySelector('.o_phonecall_details'),
        "Details should have been shown");
    assert.strictEqual(
        document
            .querySelector(`
                .o_phonecall_details
                .o_dial_phonecall_partner_name
                strong`)
            .innerHTML,
        'Partner 110',
        "Details should have been shown");

    // start call
    await testUtils.dom.click(document.querySelector('.o_dial_call_button'));
    assert.isVisible(
        document
            .querySelector('.o_phonecall_in_call'),
        "in call info should be displayed");
    assert.containsOnce(document.body, '.o_dial_hangup_button', 'Should be in call');

    // simulate end of setTimeout in demo mode or answer in prod
    this.onaccepted();
    // end call
    await testUtils.dom.click(document.querySelector('.o_dial_hangup_button'));
    assert.containsNone(document.body, '.o_dial_hangup_button', 'Should not be in call');
    assert.strictEqual(
        document
            .querySelector(`
                .o_phonecall_details
                .o_dial_phonecall_partner_name
                strong`)
            .innerHTML,
        'Partner 123',
        "Phonecall of second partner should have been displayed");

    // close details
    await testUtils.dom.click(document.querySelector('.o_phonecall_details_close'));
    assert.containsN(
        document.body, `
            .o_dial_next_activities
            .o_dial_phonecall`,
        2,
        "Next activities tab should have 2 phonecalls after first call");

    // hangup before accept call
    // select first call with autocall
    await testUtils.dom.click(document.querySelector('.o_dial_call_button'));
    assert.strictEqual(
        document
            .querySelector(`
                .o_phonecall_details
                .o_dial_phonecall_partner_name
                strong`)
            .innerHTML,
        'Partner 123',
        "Phonecall of second partner should have been displayed");

    // start call
    await testUtils.dom.click(document.querySelector('.o_dial_call_button'));
    assert.isVisible(
        document
            .querySelector('.o_phonecall_in_call'),
        "in call info should be displayed");

    // hangup before accept
    await testUtils.dom.click(document.querySelector('.o_dial_hangup_button'));
    // we won't accept this call, better clean the current onaccepted
    this.onaccepted = undefined;
    // close details
    await testUtils.dom.click(document.querySelector('.o_phonecall_details_close'));

    assert.containsN(
        document.body, `
            .o_dial_next_activities
            .o_dial_phonecall`,
        2,
        "No call should have been removed");

    // end list
    // select first call with autocall
    await testUtils.dom.click(document.querySelector('.o_dial_call_button'));
    assert.strictEqual(
        document
            .querySelector(`
                .o_phonecall_details
                .o_dial_phonecall_partner_name
                strong`)
            .innerHTML,
        'Partner 142',
        "Phonecall of third partner should have been displayed (second one has already been tried)");

    // start call
    await testUtils.dom.click(document.querySelector('.o_dial_call_button'));
    // simulate end of setTimeout in demo mode or answer in prod
    this.onaccepted();
    // end call
    await testUtils.dom.click(document.querySelector('.o_dial_hangup_button'));
    assert.strictEqual(
        document
            .querySelector(`
                .o_phonecall_details
                .o_dial_phonecall_partner_name
                strong`)
            .innerHTML,
        'Partner 123',
        "Phonecall of second partner should have been displayed");

    // start call
    await testUtils.dom.click(document.querySelector('.o_dial_call_button'));
    // simulate end of setTimeout in demo mode or answer in prod
    this.onaccepted();
    // end call
    await testUtils.dom.click(document.querySelector('.o_dial_hangup_button'));
    assert.containsNone(
        document.body, `
            .o_dial_phonecalls
            .o_dial_phonecall`,
        "The list should be empty");
    assert.strictEqual(
        counterNextActivities,
        8,
        "avoid to much call to get_next_activities_list, would be great to lower this counter");

    const incomingCallParams = {
        number: "123-456-789",
    };
    // simulate an incoming call
    messaging.messagingBus.trigger('incomingCall', { detail: incomingCallParams });
    await testUtils.nextTick();
    // Accept call
    await testUtils.dom.click(document.querySelector('.o_dial_accept_button'));

    assert.containsOnce(document.body, '.o_dial_hangup_button', 'Should be in call');

    // Hangup call
    await testUtils.dom.click(document.querySelector('.o_dial_hangup_button'));
    assert.containsNone(document.body, '.o_dial_hangup_button', 'Should not be in call');
    assert.containsOnce(
        document.body,
        '.o_phonecall_details',
        "Details should be visible");

    // simulate an incoming call
    messaging.messagingBus.trigger('incomingCall', { detail: incomingCallParams });
    await testUtils.nextTick();
    await testUtils.dom.click(document.querySelector('.o_dial_reject_button'));
    assert.containsNone(document.body, '.o_dial_hangup_button', 'Should not be in call');
    assert.containsOnce(
        document.body,
        '.o_phonecall_details',
        "Details should be visible");
    assert.verifySteps([
        'init_call',
        'hangup_call',
        'init_call',
        'canceled_call',
        'init_call',
        'hangup_call',
        'init_call',
        'hangup_call',
        'incoming_call',
        'incoming_call_accepted',
        'hangup_call',
        'incoming_call',
        'rejected_call'
    ]);
});

QUnit.test('Call from Recent tab + keypad', async function (assert) {
    assert.expect(10);

    const self = this;

    await createDialingPanel({
        async mockRPC(route, args) {
            if (args.method === 'get_pbx_config') {
                return { mode: 'demo' };
            }
            if (args.model === 'voip.phonecall') {
                switch (args.method) {
                case 'create_from_number':
                    assert.step('create_from_number');
                    self.recentList = [{
                        call_date: '2019-06-06 08:05:47',
                        create_date: '2019-06-06 08:05:47.00235',
                        create_uid: 2,
                        date_deadline: '2019-06-06',
                        direction: 'outgoing',
                        id: 0,
                        in_queue: 't',
                        name: 'Call to 123456789',
                        user_id: 2,
                        phone: '123456789',
                        start_time: 1559808347,
                        state: 'pending',
                        write_date: '2019-06-06 08:05:48.568076',
                        write_uid: 2,
                    }];
                    return self.recentList[0];
                case 'create_from_recent':
                    assert.step('create_from_recent');
                    return {id: 202};
                case 'get_recent_list':
                    return self.recentList;
                case 'get_next_activities_list':
                    return [];
                case 'init_call':
                    assert.step('init_call');
                    return [];
                case 'hangup_call':
                    assert.step('hangup_call');
                    return;
                }
            }
        },
    });

    // make a first call
    assert.containsNone(
        document.body,
        '.o_phonecall_details',
        "Details should not be visible yet");
    assert.containsNone(
        document.body, `
            .o_dial_recent
            .o_dial_phonecalls
            .o_dial_phonecall`,
        "Recent tab should have 0 phonecall at the beginning");

    // select keypad
    await testUtils.dom.click(document.querySelector('.o_dial_keypad_icon'));
    // click on 1
    await testUtils.dom.click(document.querySelectorAll('.o_dial_keypad_button')[0]);
    // click on 2
    await testUtils.dom.click(document.querySelectorAll('.o_dial_keypad_button')[1]);
    // click on 3
    await testUtils.dom.click(document.querySelectorAll('.o_dial_keypad_button')[2]);
    // click on 4
    await testUtils.dom.click(document.querySelectorAll('.o_dial_keypad_button')[3]);
    // click on 5
    await testUtils.dom.click(document.querySelectorAll('.o_dial_keypad_button')[4]);
    // click on 6
    await testUtils.dom.click(document.querySelectorAll('.o_dial_keypad_button')[5]);
    // click on 7
    await testUtils.dom.click(document.querySelectorAll('.o_dial_keypad_button')[6]);
    // click on 8
    await testUtils.dom.click(document.querySelectorAll('.o_dial_keypad_button')[7]);
    // click on 9
    await testUtils.dom.click(document.querySelectorAll('.o_dial_keypad_button')[8]);
    // call number 123456789
    await testUtils.dom.click(document.querySelector('.o_dial_call_button'));

    assert.strictEqual(
        document
            .querySelector(`
                .o_phonecall_details
                .o_phonecall_info_name
                div`)
            .innerHTML,
        'Call to 123456789',
        "Details should have been shown");
    assert.containsOnce(document.body, '.o_dial_hangup_button', 'Should be in call');

    // simulate end of setTimeout in demo mode or answer in prod
    this.onaccepted();
    // end call
    await testUtils.dom.click(document.querySelector('.o_dial_hangup_button'));
    assert.containsNone(document.body, '.o_dial_hangup_button', 'Should not be in call');

    // call number 123456789
    await testUtils.dom.click(document.querySelector('.o_dial_call_button'));
    this.onaccepted();
    // end call
    await testUtils.dom.click(document.querySelector('.o_dial_hangup_button'));
    assert.verifySteps([
        'create_from_number',
        'hangup_call',
        'create_from_recent',
        'hangup_call',
    ]);
});

QUnit.test('keyboard navigation on dial keypad input', async function (assert) {
    assert.expect(8);

    const self = this;

    await createDialingPanel({
        async mockRPC(route, args) {
            if (args.method === 'get_pbx_config') {
                return { mode: 'demo' };
            }
            if (args.model === 'voip.phonecall') {
                if (args.method === 'create_from_number') {
                    assert.step('create_from_number');
                    self.recentList = [{
                        call_date: '2019-06-06 08:05:47',
                        create_date: '2019-06-06 08:05:47.00235',
                        create_uid: 2,
                        date_deadline: '2019-06-06',
                        direction: 'outgoing',
                        id: 0,
                        in_queue: 't',
                        name: 'Call to 987654321',
                        user_id: 2,
                        phone: '987654321',
                        start_time: 1559808347,
                        state: 'pending',
                        write_date: '2019-06-06 08:05:48.568076',
                        write_uid: 2,
                    }];
                    return self.recentList[0];
                }
                if (args.method === 'get_next_activities_list') {
                    return self.phoneCallDetailsData.filter(phoneCallDetailData =>
                        !['done', 'cancel'].includes(phoneCallDetailData.state));
                }
                if (args.method === 'hangup_call') {
                    if (args.kwargs.done) {
                        for (const phoneCallDetailData of self.phoneCallDetailsData) {
                            if (phoneCallDetailData.id === args.args[0]) {
                                phoneCallDetailData.state = 'done';
                            }
                        }
                    }
                    assert.step('hangup_call');
                    return [];
                }
            }
        },
    });

    // make a first call
    assert.containsNone(document.body, '.o_phonecall_details', 'Details should not be visible yet');

    // select keypad
    await testUtils.dom.click(document.querySelector('.o_dial_keypad_icon'));
    // click on 9
    await testUtils.dom.click(document.querySelectorAll('.o_dial_keypad_button')[8]);
    // click on 8
    await testUtils.dom.click(document.querySelectorAll('.o_dial_keypad_button')[7]);
    // click on 7
    await testUtils.dom.click(document.querySelectorAll('.o_dial_keypad_button')[6]);
    // click on 6
    await testUtils.dom.click(document.querySelectorAll('.o_dial_keypad_button')[5]);
    // click on 5
    await testUtils.dom.click(document.querySelectorAll('.o_dial_keypad_button')[4]);
    // click on 4
    await testUtils.dom.click(document.querySelectorAll('.o_dial_keypad_button')[3]);
    // click on 3
    await testUtils.dom.click(document.querySelectorAll('.o_dial_keypad_button')[2]);
    // click on 2
    await testUtils.dom.click(document.querySelectorAll('.o_dial_keypad_button')[1]);
    // click on 1
    await testUtils.dom.click(document.querySelectorAll('.o_dial_keypad_button')[0]);

    // call number 987654321 (validated by pressing enter key)
    $('.o_dial_keypad_input').trigger($.Event('keyup', {keyCode: $.ui.keyCode.ENTER}));
    await testUtils.nextTick();

    assert.verifySteps(['create_from_number']);
    assert.strictEqual(document.querySelector('.o_phonecall_details .o_phonecall_info_name').innerText.trim(),
        'Call to 987654321', 'Details should have been shown');
    assert.containsOnce(document.body, '.o_dial_hangup_button', 'should be in call on pressing ENTER after dialing a phone number');

    // simulate end of setTimeout in demo mode or answer in prod
    this.onaccepted();
    // end call
    await testUtils.dom.click(document.querySelector('.o_dial_hangup_button'));
    assert.containsNone(document.body, '.o_dial_hangup_button', 'should no longer be in call after hangup');
    assert.verifySteps(['hangup_call']);
});

QUnit.test('DialingPanel is closable with the BackButton in the mobile app', async function (assert) {
    assert.expect(13);

    testUtils.mock.patch(mobile.methods, {
        overrideBackButton({ enabled }) {
            assert.step(`overrideBackButton: ${enabled}`);
        },
    });

    await createDialingPanel({
        async mockRPC(route, args) {
            if (args.method === 'get_pbx_config') {
                return { mode: 'demo' };
            }
            if (args.model === 'voip.phonecall') {
                if (args.method === 'get_next_activities_list') {
                    return [];
                }
            }
        },
    });

    assert.isVisible(document.querySelector('.o_dial'), "should be visible");
    assert.verifySteps([
        'overrideBackButton: true',
    ], "should be enabled when opened");

    // simulate 'backbutton' events triggered by the app
    await testUtils.dom.triggerEvent(document, 'backbutton');
    assert.isNotVisible(document.querySelector('.o_dial'), "should be closed");
    assert.verifySteps([
        'overrideBackButton: false',
    ], "should be disabled when closed");

    core.bus.trigger('voip_onToggleDisplay');
    await testUtils.nextTick();
    await testUtils.dom.click(document.querySelector('.o_dial_fold'));
    assert.verifySteps([
        'overrideBackButton: true',
        'overrideBackButton: false',
    ]);
    await testUtils.dom.click(document.querySelector('.o_dial_fold'));
    assert.verifySteps([
        'overrideBackButton: true',
    ], "should be enabled when unfolded");

    await testUtils.dom.click(document.querySelector('.o_dial_window_close'));
    assert.verifySteps([
        'overrideBackButton: false',
    ], "should be disabled when closed");

    testUtils.mock.unpatch(mobile.methods);
});

});
});
