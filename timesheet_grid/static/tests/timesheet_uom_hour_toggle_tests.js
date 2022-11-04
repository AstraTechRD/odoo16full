/** @odoo-module */

import { serializeDateTime } from "@web/core/l10n/dates";
import { registry } from "@web/core/registry";
import { ormService } from "@web/core/orm_service";
import { timerService } from "@timer/services/timer_service";

import { makeView } from "@web/../tests/views/helpers";
import { click, getFixture, nextTick, triggerEvent } from "@web/../tests/helpers/utils";
import { getServerData, setupTestEnv, addFieldsInArch } from "@hr_timesheet/../tests/hr_timesheet_common_tests";

const { DateTime } = luxon;


QUnit.module("timesheet_grid", (hooks) => {
    let target;
    let makeViewArgs;
    let now = DateTime.utc();
    const mockGetServerTimeRPC = function (route, { args, method }) {
        if (method === "get_server_time") {
            return Promise.resolve(serializeDateTime(now));
        }
    };
    hooks.beforeEach(async function (assert) {
        setupTestEnv();
        registry.category("services").add("orm", ormService, {force: true});
        registry.category("services").add("timer", timerService, {force: true});

        const serverData = getServerData();
        serverData.models["account.analytic.line"].fields.timer_start = { string: "Timer Started", type: 'datetime' };
        serverData.models["account.analytic.line"].fields.timer_pause = { string: "Timer Paused", type: 'datetime' };
        serverData.models["account.analytic.line"].fields.duration_unit_amount = { string: "Duration Unit Amount", type: 'float' };
        serverData.models["account.analytic.line"].fields.is_timer_running = { string: "Is Timer Running", type: 'boolean' };
        addFieldsInArch(serverData, ["timer_start", "timer_pause", "duration_unit_amount", "is_timer_running"], "unit_amount");

        serverData.views["account.analytic.line,false,kanban"] = `
            <kanban>
                <templates>
                    <field name="timer_start" invisible="1"/>
                    <field name="timer_pause" invisible="1"/>
                    <field name="duration_unit_amount" invisible="1"/>
                    <field name="is_timer_running" invisible="1"/>
                    <t t-name="kanban-box">
                        <div><field name="unit_amount" widget="timesheet_uom_hour_toggle"/></div>
                    </t>
                </templates>
            </kanban>
        `;

        for (let index = 0; index < serverData.models["account.analytic.line"].records.length; index++) {
            const record = serverData.models["account.analytic.line"].records[index];
            record.timer_start = index % 3 ? serializeDateTime(now.minus({ days: 1 })) : false;
            record.timer_pause = index % 2 && record.timer_start ? serializeDateTime(now.minus({ hours: 1 })) : false;
            record.duration_unit_amount = record.unit_amount;
            record.is_timer_running = record.timer_start && !record.timer_pause;
        }

        makeViewArgs = {
            type: "kanban",
            resModel: "account.analytic.line",
            serverData,
            mockRPC: (route, { args, method }) => mockGetServerTimeRPC(route, { args, method }),
        };
        target = getFixture();
    });

    QUnit.module("timesheet_uom_hour_toggle");

    function _checkCardButton(card, isTimerRunning, assert) {
        assert.containsOnce(
            card,
            `div[name="unit_amount"] .o_kanban_timer_start button i.fa-${ isTimerRunning ? "stop" : "play" }-circle`,
            `Right class should be applied on button. Expected "fa-${ isTimerRunning ? "stop" : "play" }-circle"`
        );
    }

    QUnit.test("button' icon is according to is_timer_running", async function (assert) {
        await makeView(makeViewArgs);
        const secondCard = target.querySelector(".o_kanban_renderer .o_kanban_record:nth-of-type(2)");
        const thirdCard = target.querySelector(".o_kanban_renderer .o_kanban_record:nth-of-type(3)");
        await triggerEvent(secondCard, ".o_kanban_timer_start", "mouseover");
        await nextTick();
        _checkCardButton(secondCard, false, assert);
        await triggerEvent(thirdCard, ".o_kanban_timer_start", "mouseover");
        await nextTick();
        _checkCardButton(thirdCard, true, assert);
    });

    QUnit.test("button is displayed on hover", async function (assert) {
        await makeView(makeViewArgs);
        const secondCard = target.querySelector(".o_kanban_renderer .o_kanban_record:nth-of-type(2)");
        assert.containsOnce(secondCard, ".o_kanban_timer_start span");
        assert.containsNone(secondCard, ".o_kanban_timer_start button");
        await triggerEvent(secondCard, ".o_kanban_timer_start", "mouseover");
        await nextTick();
        assert.containsOnce(secondCard, ".o_kanban_timer_start button");
        assert.containsNone(secondCard, ".o_kanban_timer_start span");
        await triggerEvent(secondCard, ".o_kanban_timer_start", "mouseout");
        await nextTick();
        assert.containsOnce(secondCard, ".o_kanban_timer_start span");
        assert.containsNone(secondCard, ".o_kanban_timer_start button");
    });

    QUnit.test("correct rpc calls are performed (click decrease)", async function (assert) {
        const mockRPC = function (route, { args, method }) {
            if (method === "action_timer_decrease") {
                assert.step("action_timer_decrease");
                return Promise.resolve(true);
            } else {
                return mockGetServerTimeRPC(...arguments);
            }
        };
        await makeView({ ...makeViewArgs, mockRPC });
        const secondRow = target.querySelector('.o_kanban_renderer .o_kanban_record:nth-of-type(2)');
        await click(secondRow, 'div[name="unit_amount"] button.fa-minus');
        assert.verifySteps(["action_timer_decrease"]);
    });

    QUnit.test("correct rpc calls are performed (click increase)", async function (assert) {
        const mockRPC = function (route, { args, method }) {
            if (method === "action_timer_increase") {
                assert.step("action_timer_increase");
                return Promise.resolve(true);
            } else {
                return mockGetServerTimeRPC(...arguments);
            }
        };
        await makeView({ ...makeViewArgs, mockRPC });
        const secondRow = target.querySelector('.o_kanban_renderer .o_kanban_record:nth-of-type(2)');
        await click(secondRow, 'div[name="unit_amount"] button.fa-plus');
        assert.verifySteps(["action_timer_increase"]);
    });

});
