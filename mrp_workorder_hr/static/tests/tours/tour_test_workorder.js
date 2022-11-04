/** @odoo-module **/

import tour from 'web_tour.tour';
import helper from 'mrp_workorder.tourHelper';

tour.register('test_production_with_employee', {test: true}, [
    {trigger: 'div.popup'},
    {trigger: 'h3:contains("Change Worker")'},
    {trigger: 'div.selection-item:contains("Arthur")'},
    {trigger: 'div.popup-numpad'},
    {trigger: '.popup-numpad button:contains("1")'},
    {trigger: 'span.highlight:contains("•")'},
    {trigger: '.popup-numpad button:contains("2")'},
    {trigger: 'span.highlight:contains("••")'},
    {trigger: '.popup-numpad button:contains("3")'},
    {trigger: 'span.highlight:contains("•••")'},
    {trigger: '.popup-numpad button:contains("4")'},
    {trigger: 'span.highlight:contains("••••")'},
    {trigger: 'button.confirm'},
    {
        trigger: 'span[title="Arthur Fu"]',
        run: function () {
            helper.assertCheckLength(3);
            helper.assertValidatedCheckLength(0);
            helper.assertQtyToProduce(2, 2);
            helper.assertCurrentCheck('Instruction 1');
        }
    },
    {trigger: 'div[name=employee_name]'},
    {trigger: 'button.btn-link:contains("New")'},
    {trigger: 'h3:contains("Change Worker")'},
    {trigger: 'div.selection-item:contains("Thomas")'},
    {trigger: 'div.popup-numpad'},
    {trigger: '.popup-numpad button:contains("5")'},
    {trigger: 'span.highlight:contains("•")'},
    {trigger: '.popup-numpad button:contains("6")'},
    {trigger: 'span.highlight:contains("••")'},
    {trigger: '.popup-numpad button:contains("7")'},
    {trigger: 'span.highlight:contains("•••")'},
    {trigger: '.popup-numpad button:contains("8")'},
    {trigger: 'span.highlight:contains("••••")'},
    {trigger: 'button.confirm'},
    {
        trigger: 'span[title="Thomas Nific"]',
        run: function () {
            helper.assertCheckLength(3);
            helper.assertValidatedCheckLength(0);
            helper.assertQtyToProduce(2, 2);
            helper.assertCurrentCheck('Instruction 1');
        }
    },
    {trigger: 'div[name=employee_name]'},
    {trigger: 'button.btn_employee:contains("Thomas")'},
    {trigger: 'button[name="action_next"]'},
    {trigger: 'div[name=qty_producing]:contains("2")'}, //field become readonly
    {
        trigger: '.o_tablet_step_ok',
        run: function () {
            helper.assertCheckLength(3);
            helper.assertValidatedCheckLength(1);
            helper.assertQtyToProduce(2, 2);
            helper.assertCurrentCheck('Instruction 2');
        }
    },
    {trigger: 'button[name="action_next"]'},
    {
        trigger: 'p:contains("third")',
        run: function () {
            helper.assertCheckLength(3);
            helper.assertValidatedCheckLength(2);
            helper.assertQtyToProduce(2, 2);
            helper.assertCurrentCheck('Instruction 3');
        }
    },
    {trigger: 'button[name=openMenuPopup]'},
    {trigger: '.o_tablet_popups'},
    {trigger: '.btn:contains("Update Instruction")'},
    {trigger: '.modal-title:contains("Update Instruction")'},
    // {
    //     trigger: "div[name=note] p",
    //     position: 'bottom',
    //     run: 'text my new instruction',
    // }, {
    {
        trigger: "input#comment",
        position: 'bottom',
        run: 'text my reason',
    },
    {trigger: '.btn-primary[name="process"]'},
    {trigger: '.o_tablet_client_action'},
    {trigger: '.btn-primary[name="action_next"]'},
    {trigger: '.btn[name=do_finish]'},
    {trigger: '.o_searchview_input'},
]);
