/** @odoo-module **/
import tour from 'web_tour.tour';


tour.register('industry_fsm_sale_products_tour', {
    test: true,
    url: "/web",
}, [{
    trigger: '.o_app[data-menu-xmlid="industry_fsm.fsm_menu_root"]',
    content: 'Go to industry FSM',
    position: 'bottom',
}, {
    trigger: 'input.o_searchview_input',
    content: 'Search Field Service task',
    run: `text Fsm task`,
}, {
    trigger: '.o_searchview_autocomplete .o_menu_item:contains("Fsm task")',
    content: 'Validate search',
}, {
    trigger: '.o_kanban_record div[name="name"]:contains("Fsm task")',
    content: 'Open task',
}, {
    trigger: 'button[name="action_fsm_view_material"] div[name="material_line_total_price"] span:contains("~M~")',
    content: 'The currency that is display in the stat button is the one from the price list of the task partner',
}, {
    trigger: '.o_fsm_material_kanban .o_kanban_record:contains("Consommable product ordered") button[name="fsm_add_quantity"]',
    content: 'Add 1 quantity',
}, {
    trigger: '.o_fsm_material_kanban .o_kanban_record:contains("1,000.00") div[name="fsm_quantity"]:contains("1") button[name="fsm_add_quantity"]',
    content: 'Price is 1000, quantity is 1 and add 1 quantity',
}, {
    trigger: '.o_fsm_material_kanban .o_kanban_record:contains("500.00") div[name="fsm_quantity"] span:contains("2")',
    content: 'Price is 500',
}]);
