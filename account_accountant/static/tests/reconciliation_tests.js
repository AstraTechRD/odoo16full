odoo.define('account_accountant.ReconciliationTests', function (require) {
    "use strict";

    var testUtils = require('web.test_utils');
    var ManualAction = require('account.ReconciliationClientAction').ManualAction;

    var options = {
        context: {
        },
    };

    QUnit.module('account', {
    }, function () {
        QUnit.module('ReconciliationUtils');

        QUnit.test('Reconciliation Utils: float compare', async function (assert) {
            assert.expect(8);

            var clientAction = new ManualAction(null, options);
            var session = {
                    currencies: {
                        3: {
                            digits: [69, 2],
                            position: "before",
                            symbol: "$"
                        }
                    }
            };
            await testUtils.mock.addMockEnvironment(clientAction, {
                session: session,
            });
            var amounts = [
                [258.49, 258.50, -1],
                [0.02, 0.03, -1],
                [0.99, 1.00, -1],
                [258.50, 258.49, 1],
                [0.03, 0.02, 1],
                [1.00, 0.99, 1],
                [0.01, 0.01, 0],
                [956.0600000000001, 956.06, 0],
            ];
            var currency_id = 3;

            for (let i = 0; i < amounts.length; i++) {
                assert.strictEqual(clientAction.model._amountCompare(amounts[i][0], amounts[i][1], currency_id), amounts[i][2], "should compare the float amounts correctly");
            }
            clientAction.destroy();
        });
    });
});
