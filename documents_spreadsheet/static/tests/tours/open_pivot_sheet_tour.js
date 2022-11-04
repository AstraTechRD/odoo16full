odoo.define("documents_spreadsheet.open_pivot_sheet_tour", function (require) {
    "use strict";

    require("web.dom_ready");
    const tour = require("web_tour.tour");

    function assert(current, expected, info) {
        if (current !== expected) {
            fail(info + ': "' + current + '" instead of "' + expected + '".');
        }
    }

    function fail(errorMessage) {
        tour._consume_tour(tour.running_tour, errorMessage);
    }

    const SHEETNAME = "Partner Spreadsheet Test";
    tour.register(
        "spreadsheet_open_pivot_sheet",
        {
            test: true,
        },
        [
            {
                trigger: '.o_app[data-menu-xmlid="documents.menu_root"]',
                content: "Open document app",
                run: "click",
            },
            {
                trigger: `div[title="${SHEETNAME}"]`,
                content: "Select Test Sheet",
                run: "click",
            },
            {
                trigger: `button.o_switch_view.o_list`,
                content: "Switch to list view",
                run: "click",
            },
            {
                trigger: `img[title="${SHEETNAME}"]`,
                content: "Open the sheet",
                run: "click",
            },
            {
                trigger: "div.o_topbar_filter_icon",
                content: "Open Filters",
                run: "click",
            },
            {
                trigger: "div.pivot_filter",
                content: "",
                run: function (actions) {
                    const pivots = document.querySelectorAll("div.pivot_filter");
                    assert(pivots.length, 1, "There should be one filter");
                    const pivot = pivots[0];
                    assert(
                        pivot.querySelector("div.o_side_panel_title").textContent,
                        "MyFilter1",
                        "Invalid filter name"
                    );
                    assert(
                        Boolean(
                            pivot.querySelector(
                                'div.o_field_many2many_tags span.badge[title="Azure Interior"]'
                            )
                        ),
                        true,
                        "Wrong default filter value"
                    );
                    actions.click(pivot.querySelector(".o_side_panel_filter_icon.fa-cog"));
                },
            },
            {
                trigger: ".o_spreadsheet_filter_editor_side_panel",
                content: "Check filter values",
                run: function () {
                    const defaultFilterValue = document.querySelectorAll(
                        'div.o_field_many2many_tags span.badge[title="Azure Interior"]'
                    );
                    assert(
                        defaultFilterValue.length,
                        1,
                        "There should be a default value in the filter..."
                    );
                    assert(
                        document.querySelector(".o_side_panel_related_model input").value,
                        "Contact",
                        "Wrong model selected"
                    );

                    const fieldsValue = document.querySelector(
                        "div.o_field_selector_value span.o_field_selector_chain_part"
                    );
                    assert(fieldsValue.textContent.trim(), "Related Company");
                },
            },
            {
                trigger: ".o_menu_brand",
                content: "Go back to the menu",
                run: "click",
            },
            {
                trigger: ".o_document_spreadsheet:first",
                content: "Sheet is visible in Documents",
            },
        ]
    );
});
