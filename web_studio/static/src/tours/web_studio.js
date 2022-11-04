/** @odoo-module */

import { _t } from "web.core";
import utils from "web_studio.utils";
import tour from "web_tour.tour";

tour.register(
    "web_studio_home_menu_background_tour",
    {
        url: "/web",
        sequence: 260,
    },
    [
        {
            trigger: ".o_web_studio_navbar_item",
            content: _t("Want to customize the background? Let’s activate <b>Odoo Studio</b>."),
            position: "bottom",
            extra_trigger: ".o_home_menu",
        },
        {
            trigger: ".o_web_studio_home_studio_menu .dropdown-toggle",
            content: _t("Click here."),
            position: "right",
        },
        {
            trigger:
                ".o_web_studio_home_studio_menu .dropdown-menu .dropdown-item.o_web_studio_change_background",
            content: _t("Change the <b>background</b>, make it yours."),
            position: "bottom",
        },
    ]
);

tour.register(
    "web_studio_new_app_tour",
    {
        url: "/web#action=studio&mode=home_menu",
        sequence: 270,
    },
    [
        {
            trigger: ".o_web_studio_new_app",
            auto: true,
            position: "bottom",
        },
        {
            trigger: ".o_web_studio_app_creator_next",
            content: _t("I bet you can <b>build an app</b> in 5 minutes. Ready for the challenge?"),
            position: "top",
        },
        {
            trigger: ".o_web_studio_app_creator_name > input",
            content: _t("How do you want to <b>name</b> your app? Library, Academy, …?"),
            position: "right",
            run: "text " + utils.randomString(6),
        },
        {
            trigger: ".o_web_studio_selectors .o_web_studio_selector:eq(2)",
            content: _t("Now, customize your icon. Make it yours."),
            position: "top",
        },
        {
            trigger: ".o_web_studio_app_creator_next.is_ready",
            content: _t("Go on, you are almost done!"),
            position: "top",
        },
        {
            trigger: ".o_web_studio_app_creator_menu > input",
            content: _t("How do you want to name your first <b>menu</b>? My books, My courses?"),
            position: "right",
            run: "text " + utils.randomString(6),
        },
        {
            trigger: ".o_web_studio_app_creator_next.is_ready",
            content: _t(
                "Continue to configure some typical behaviors for your new type of object."
            ),
            position: "bottom",
        },
        {
            trigger: ".o_web_studio_model_configurator_next",
            content: _t(
                "All set? You are just one click away from <b>generating your first app</b>."
            ),
            position: "bottom",
        },
        {
            trigger:
                ".o_web_studio_sidebar .o_web_studio_field_type_container:eq(1) .o_web_studio_field_char",
            content: _t(
                "Nicely done! Let’s build your screen now; <b>drag</b> a <i>text field</i> and <b>drop</b> it in your view, on the right."
            ),
            position: "bottom",
            run: "drag_and_drop .o_web_studio_form_view_editor .o_inner_group",
            timeout: 60000 /* previous step reloads registry, etc. - could take a long time */,
        },
        {
            trigger: ".o_web_studio_form_view_editor .o_wrap_label label",
            content: _t("To <b>customize a field</b>, click on its <i>label</i>."),
            position: "bottom",
        },
        {
            trigger: '.o_web_studio_sidebar_content.o_display_field input[name="string"]',
            content: _t(
                "Here, you can <b>name</b> your field (e.g. Book reference, ISBN, Internal Note, etc.)."
            ),
            position: "bottom",
            run: "text My Field",
        },
        {
            // wait for the field to be renamed
            extra_trigger: ".o_web_studio_form_view_editor .o_wrap_label label:contains(My Field)",
            trigger: ".o_web_studio_sidebar .o_web_studio_new",
            content: _t("Good job! To add more <b>fields</b>, come back to the <i>Add tab</i>."),
            position: "bottom",
            // the rename operation (/web_studio/rename_field + /web_studio/edit_view)
            // takes a while and sometimes reaches the default 10s timeout
            timeout: 20000,
            async run() {
                // During the rename, the UI is blocked. When the rpc returns, the UI is
                // unblocked and the sidebar is re-rendered. Without this, the step is
                // sometimes executed exactly when the sidebar is about to be replaced,
                // and it doesn't work. We thus here wait for 1s to ensure that the
                // sidebar has been re-rendered, before going further.
                // note1: there's nothing in the DOM that could be used to determine that
                // we're ready to continue (the sidebar is just replaced by itself, same state)
                // note2: ideally, it should work whenever we click, but with the current
                // architecture of studio, it's really hard to fix. Hopefully, when studio
                // will be converted to owl, this should no longer be an issue.
                await new Promise((r) => setTimeout(r, 1000));
                $(".o_web_studio_sidebar .o_web_studio_new").click();
            },
        },
        {
            trigger:
                ".o_web_studio_sidebar .o_web_studio_field_type_container:eq(1) .o_web_studio_field_selection",
            content: _t(
                "Drag & drop <b>another field</b>. Let’s try with a <i>selection field</i>."
            ),
            position: "bottom",
            run: "drag_and_drop .o_web_studio_form_view_editor .o_inner_group",
        },
        {
            trigger: ".o_web_studio_field_dialog_form > .o_web_studio_add_selection input",
            content: _t(
                "Create your <b>selection values</b> (e.g.: Romance, Polar, Fantasy, etc.)"
            ),
            position: "top",
            run: "text " + utils.randomString(6),
        },
        {
            trigger:
                ".o_web_studio_field_dialog_form > .o_web_studio_add_selection .o_web_studio_add_selection_value",
            auto: true,
        },
        {
            trigger: ".modal-footer > button:eq(0)",
            auto: true,
        },
        {
            trigger: ".o_web_studio_sidebar_text",
            auto: true,
        },
        {
            trigger: ".o_web_studio_form_view_editor .o_Chatter",
            content: _t("Click to edit messaging features on your model."),
            position: "top",
            timeout: 15000, // this can take some time on 'slow' builds (coverage, etc.)
        },
        {
            trigger: '.o_web_studio_sidebar .o_display_chatter input[name="email_alias"]',
            content: _t(
                "Set an <b>email alias</b>. Then, try to send an email to this address; it will create a document automatically for you. Pretty cool, huh?"
            ),
            position: "bottom",
        },
        {
            trigger: ".o_web_studio_leave",
            content: _t(
                "Let’s check the result. Close Odoo Studio to get an <b>overview of your app</b>."
            ),
            position: "left",
        },
        {
            trigger: ".o_field_char.o_required_modifier > input",
            auto: true,
            position: "bottom",
        },
        {
            trigger: ".o_control_panel .o_form_button_save",
            content: _t("Save."),
            position: "right",
        },
        {
            trigger: ".o_web_studio_navbar_item",
            extra_trigger: ".o_form_view .o_form_saved",
            content: _t(
                "Wow, nice! And I’m sure you can make it even better! Use this icon to open <b>Odoo Studio</b> and customize any screen."
            ),
            position: "bottom",
        },
        {
            trigger: ".o_web_studio_menu .o_menu_sections li:contains(Views)",
            content: _t("Want more fun? Let’s create more <b>views</b>."),
            position: "bottom",
        },
        {
            trigger:
                '.o_web_studio_view_category .o_web_studio_view_type.o_web_studio_inactive[data-type="kanban"] .o_web_studio_thumbnail',
            content: _t("What about a <b>Kanban view</b>?"),
            position: "bottom",
        },
        {
            trigger: ".o_web_studio_sidebar .o_web_studio_new",
            content: _t("Now you’re on your own. Enjoy your <b>super power</b>."),
            position: "bottom",
        },
    ]
);
