odoo.define("documents_spreadsheet.create_empty_sheet_tour", function (require) {
    "use strict";

    require("web.dom_ready");
    const tour = require("web_tour.tour");

    tour.register(
        "spreadsheet_create_empty_sheet",
        {
            test: true,
        },
        [
            tour.stepUtils.showAppsMenuItem(),
            {
                trigger: '.o_app[data-menu-xmlid="documents.menu_root"]',
                content: "Open document app",
                run: "click",
            },
            {
                trigger: ".o_documents_kanban_spreadsheet",
                content: "Open template dialog",
                run: "click",
            },
            {
                trigger: ".o-spreadsheet-create",
                content: "Create new spreadsheet",
                run: "click",
            },
            {
                trigger: 'div[title="Fill Color"]',
                content: "Choose a color",
                run: "click",
            },
            {
                trigger: '.o-color-picker-line-item[data-color="#990000"]',
                content: "Choose a color",
                run: "click",
            },
            {
                trigger: ".o_menu_brand",
                content: "Go back to the menu",
                run: "click",
            },
            {
                trigger: ".o_document_spreadsheet:first",
                content: "Reopen the sheet",
                run: "click",
            },
        ]
    );
    tour.register(
        "spreadsheet_create_list_view",
        {
            test: true,
        },
        [
            tour.stepUtils.showAppsMenuItem(),
            {
                trigger: '.o_app[data-menu-xmlid="documents.menu_root"]',
                content: "Open document app",
                run: "click",
            },
            {
                trigger: "button.o_switch_view.o_list",
                content: "Switch to list view",
                run: "click",
            },
            {
                trigger: ".o_favorite_menu button",
                extra_trigger: ".o_list_view, .o_legacy_list_view",
                content: "Open the favorites menu",
                run: "click",
            },
            {
                trigger: ".o_insert_list_spreadsheet_menu",
                content: "Insert in spreadsheet",
                run: "click",
            },
            {
                trigger: ".modal-footer .btn-primary",
                content: "Confirm",
                run: "click",
            },
            {
                trigger: ".o-topbar-topleft .o-topbar-menu[data-id='data']",
                content: "Open Data menu",
                run: "click",
            },
            {
                trigger: ".o-menu-item[data-name='item_list_1']",
                content: "Open List Side Panel",
                run: "click",
            },
            {
                trigger: ".o_pivot_cancel",
                content: "Go back to the list of lists",
                run: "click",
            },
        ]
    );
});
