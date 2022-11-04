/** @odoo-module */

import SpreadsheetCollaborativeChannel from "@spreadsheet_edition/bundle/o_spreadsheet/collaborative/spreadsheet_collaborative_channel";
import makeTestEnvironment from "web.test_env";

const { EventBus } = owl;

class MockBusService {
    constructor() {
        this.channels = [];
        this._bus = new EventBus();
    }

    addChannel(name) {
        this.channels.push(name);
    }

    addEventListener(eventName, handler) {
        this._bus.addEventListener("notif", handler);
    }

    notify(message) {
        this._bus.trigger("notif", [message]);
    }
}

QUnit.module("spreadsheet_edition > SpreadsheetCollaborativeChannel", {
    beforeEach: function () {
        const busService = new MockBusService();
        const rpc = function (route, params) {
            // Mock the server behavior: new revisions are pushed in the bus
            if (params.method === "dispatch_spreadsheet_message") {
                const [documentId, message] = params.args;
                busService.notify({ type: "spreadsheet", payload: { id: documentId, message } });
            }
        };
        this.env = makeTestEnvironment({ services: { bus_service: busService } }, rpc);
    },
});

QUnit.test("sending a message forward it to the registered listener", function (assert) {
    assert.expect(3);
    const channel = new SpreadsheetCollaborativeChannel(this.env, "my.model", 5);
    channel.onNewMessage("anId", (message) => {
        assert.step("message");
        assert.strictEqual(message.message, "hello", "It should have the correct message content");
    });
    channel.sendMessage("hello");
    assert.verifySteps(["message"], "It should have received the message");
});

QUnit.test("previous messages are forwarded when registering a listener", function (assert) {
    assert.expect(3);
    const channel = new SpreadsheetCollaborativeChannel(this.env, "my.model", 5);
    channel.sendMessage("hello");
    channel.onNewMessage("anId", (message) => {
        assert.step("message");
        assert.strictEqual(message.message, "hello", "It should have the correct message content");
    });
    assert.verifySteps(["message"], "It should have received the pending message");
});

QUnit.test("the channel does not care about other bus messages", function (assert) {
    assert.expect(1);
    const channel = new SpreadsheetCollaborativeChannel(this.env, "my.model", 5);
    channel.onNewMessage("anId", () => assert.step("message"));
    this.env.services.bus_service.notify("a-random-channel", "a-random-message");
    assert.verifySteps([], "The message should not have been received");
});
