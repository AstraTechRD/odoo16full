/** @odoo-module **/

import tour from 'web_tour.tour';
import helper from 'mrp_workorder.tourHelper';

tour.register('test_add_component', {test: true}, [
    {
        trigger: '.o_tablet_client_action',
        run: function () {
            helper.assertCheckLength(2);
            helper.assertValidatedCheckLength(0);
            helper.assertQtyToProduce(1, 1);
            helper.assertCurrentCheck('Register Consumed Materials "Elon Musk"');
            helper.assertComponent('Elon Musk', 'readonly', 1, 1);
        }
    },
    {trigger: '.btn[name="button_start"]'},
    {
        trigger: '.o_workorder_icon_btn',
        extra_trigger: '.btn[name="button_pending"]',
    },
    {trigger: '.o_tablet_popups'},
    {trigger: '.btn:contains("Add Component")'},
    {trigger: '.modal-title:contains("Add Component")'},
    {
        trigger: "div.o_field_widget[name='product_id'] input ",
        position: 'bottom',
        run: 'text extra',
    }, {
        trigger: '.ui-menu-item > a:contains("extra")',
        in_modal: false,
        auto: true,
    }, {
        trigger: "div.o_field_widget[name='product_qty'] input",
        in_modal: true,
        position: 'bottom',
        run: 'text 3',
    },
    {trigger: '.btn-primary[name="add_product"]'},
    {
        trigger: '.o_tablet_client_action',
        run: function () {
            helper.assertCheckLength(3);
            helper.assertValidatedCheckLength(0);
            helper.assertQtyToProduce(1, 1);
            helper.assertCurrentCheck('Register Consumed Materials "extra"');
            helper.assertComponent('extra', 'editable', 3, 3);
        }
    }, {
        trigger: "div.o_field_widget[name='lot_id'] input ",
        position: 'bottom',
        run: 'text lot1',
    }, {
        trigger: '.ui-menu-item > a:contains("lot1")',
        in_modal: false,
        auto: true,
    }, {
        trigger: '.o_tablet_client_action',
        run: () => {
            helper.assertCheckLength(3);
            helper.assertValidatedCheckLength(0);
            helper.assertQtyToProduce(1, 1);
            helper.assertCurrentCheck('Register Consumed Materials "extra"');
            helper.assertComponent('extra', 'editable', 3, 3);
            helper.assert($('div.o_field_widget[name="lot_id"] input').val(), 'lot1');
        }
    },
    // go to Elon Musk step (second one since 'extra')
    {trigger: '.o_tablet_step:nth-child(2)'},
    {trigger: '.o_selected:contains("Elon")'},
    {
        trigger: '.o_tablet_client_action',
        run: function () {
            helper.assertCheckLength(3);
            helper.assertValidatedCheckLength(0);
            helper.assertQtyToProduce(1, 1);
            helper.assertCurrentCheck('Register Consumed Materials "Elon Musk"');
            helper.assertComponent('Elon Musk', 'readonly', 1, 1);
        }
    },
    // go to metal cylinder step
    {trigger: '.btn[name="action_next"]'},
    {trigger: 'div[name="component_id"]:contains("Metal")'},
    {
        trigger: '.o_tablet_client_action',
        run: function () {
            helper.assertComponent('Metal cylinder', 'editable', 2, 2);
            helper.assertCheckLength(3);
            helper.assertValidatedCheckLength(1);
            helper.assertQtyToProduce(1, 1);
            helper.assertCurrentCheck('Register Consumed Materials "Metal cylinder"');
        }
    }, {
        trigger: 'input[id="qty_done"]',
        position: 'bottom',
        run: 'text 1',
    }, {
        trigger: 'div.o_field_widget[name="lot_id"] input',
        position: 'bottom',
        run: 'text mc1',
    },
    {trigger: '.o_workorder_icon_btn'},
    {trigger: '.o_tablet_popups'},
    {trigger: '.btn:contains("Add By-product")'},
    {trigger: '.modal-title:contains("Add By-Product")'},
    {
        trigger: "div.o_field_widget[name='product_id'] input ",
        position: 'bottom',
        run: 'text extra-bp',
    }, {
        trigger: '.ui-menu-item > a:contains("extra-bp")',
        in_modal: false,
        auto: true,
    }, {
        trigger: "div.o_field_widget[name='product_qty'] input",
        in_modal: true,
        position: 'bottom',
        run: 'text 1',
    },
    {trigger: '.btn-primary[name="add_product"]'},
    {
        trigger: '.o_tablet_client_action',
        run: function () {
            helper.assertCheckLength(4);
            helper.assertValidatedCheckLength(1);
            helper.assertQtyToProduce(1, 1);
            helper.assertCurrentCheck('Register By-products "extra-bp"');
            helper.assertComponent('extra-bp', 'editable', 1, 1);
        }
    }, {
        trigger: "div.o_field_widget[name='lot_id'] input ",
        position: 'bottom',
        run: 'text lot2',
    }, {
        trigger: '.ui-menu-item > a:contains("lot2")',
        in_modal: false,
        auto: true,
    },
    {trigger: '.btn[name=action_next]'},
    {
        trigger: 'div[name="component_id"]:contains("Metal")',
        run: function () {
            helper.assertCheckLength(4);
            helper.assertValidatedCheckLength(2);
            helper.assertQtyToProduce(1, 1);
            helper.assertCurrentCheck('Register Consumed Materials "Metal cylinder"');
            helper.assertComponent('Metal cylinder', 'editable', 2, 2);
        }
    },
    {trigger: '.btn[name=action_next]'},
    // go back to the first not done check
    {
        trigger: 'div[name="component_id"]:contains("extra")',
        run: function () {
            helper.assertComponent('extra', 'editable', 3, 3);
            helper.assertCheckLength(4);
            helper.assertValidatedCheckLength(3);
            helper.assertQtyToProduce(1, 1);
            helper.assertCurrentCheck('Register Consumed Materials "extra"');
        }
    },
    {trigger: '.btn[name=action_next]'},
    // we have the rainbow man once
    {
        trigger: '.o_tablet_step:nth-child(5)',
        run: function () {
            helper.assertRainbow(true);
        }
    },
    {trigger: '.o_reward_rainbow_man'},
    {
        trigger: 'h1:contains("Good Job")',
        run: function () {
            helper.assertDoneButton(true);
        }
    },
    // we do not have it twice
    {trigger: '.o_tablet_step:nth-child(2)'},
    {
        trigger: 'div[name="component_id"]:contains("Elon")',
        run: function () {
            helper.assertCheckLength(5);
            helper.assertValidatedCheckLength(4);
            helper.assertQtyToProduce(1, 1);
            helper.assertCurrentCheck('Register Consumed Materials "Elon Musk"');
            helper.assertComponent('Elon Musk', 'readonly', 1, 0);
        }
    },
    {trigger: '.o_tablet_step:nth-child(5)'},
    {
        trigger: 'h1:contains("Good Job")',
        run: function () {
            helper.assertRainbow(false);
            helper.assertDoneButton(true);
        }
    },
    {
        trigger: "input[id='finished_lot_id']",
        position: 'bottom',
        run: 'text F0001',
    },
    {
        trigger: '.ui-menu-item > a:contains("F0001")',
        in_modal: false,
        auto: true,
    },
    {trigger: '.btn[name=do_finish]'},
    {trigger: '.o_searchview_input'},
]);

tour.register('test_add_step', {test: true}, [
    {
        trigger: '.o_tablet_client_action',
        run: function () {
            helper.assertCheckLength(1);
            helper.assertValidatedCheckLength(0);
            helper.assertQtyToProduce(1, 1);
            helper.assertCurrentCheck('Register Consumed Materials "Metal cylinder"');
            helper.assertComponent('Metal cylinder', 'editable', 2, 2);
        }
    },
    {trigger: '.btn[name="button_start"]'},
    {
        trigger: '.o_workorder_icon_btn',
        extra_trigger: '.btn[name="button_pending"]',
    },
    {trigger: '.o_tablet_popups'},
    {trigger: '.btn:contains("Add a Step")'},
    {trigger: '.modal-title:contains("Add a Step")'},
    {
        trigger: "div[name=title] input",
        position: 'bottom',
        run: 'text my very new step',
    }, {
        trigger: "div[name=note] p",
        position: 'bottom',
        run: 'text why am I adding a step',
    },
    {trigger: '.btn-primary[name="add_check_in_chain"]'},
    {
        trigger: '.o_tablet_client_action',
        run: function () {
            helper.assertCheckLength(2);
            helper.assertValidatedCheckLength(0);
            helper.assertQtyToProduce(1, 1);
            helper.assertCurrentCheck('Register Consumed Materials "Metal cylinder"');
            helper.assertComponent('Metal cylinder', 'editable', 2, 2);
        }
    },
    // go to new step
    {trigger: '.o_tablet_step:nth-child(2)'},
    {trigger: 'div:contains("why am I")'},
    {
        trigger: '.o_tablet_client_action',
        run: function () {
            helper.assertCheckLength(2);
            helper.assertValidatedCheckLength(0);
            helper.assertQtyToProduce(1, 1);
            helper.assertCurrentCheck("my very new step");
        }
    },
    {trigger: 'div[name=note]:contains("why am I adding a step")'},
    {trigger: '.o_tablet_client_action'},
    {trigger: '.o_tablet_step:nth-child(1)'},
    {
        trigger: 'span:contains("Metal")',
        run: function () {
            helper.assertCheckLength(2);
            helper.assertValidatedCheckLength(0);
            helper.assertQtyToProduce(1, 1);
            helper.assertCurrentCheck('Register Consumed Materials "Metal cylinder"');
            helper.assertComponent('Metal cylinder', 'editable', 2, 2);
        }
    },
    {trigger: 'button[name=openMenuPopup]'},
    {trigger: '.o_tablet_popups'},
    {trigger: '.btn:contains("Update Instruction")'},
    {trigger: '.modal-title:contains("Update Instruction")'},
    {
        trigger: 'input#comment',
        run: 'text my reason',
    },

    {trigger: '.btn-primary[name="process"]'},
    {trigger: '.o_tablet_client_action'},
    {trigger: '.btn[name=action_next]'},
    {trigger: 'div[name=note]:contains("why am I adding a step")'},
    {trigger: '.btn[name=action_next]'},
    {trigger: '.btn[name=action_generate_serial]'},
    {trigger: '.btn[name=do_finish]'},
    {trigger: '.o_searchview_input'},
]);
