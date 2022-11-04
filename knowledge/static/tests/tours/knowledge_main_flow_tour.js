/** @odoo-module */

/**
 * Global Knowledge flow tour.
 * Features tested:
 * - Create an article
 * - Change its title / content
 * - Share an article with a created partner
 * - Create 2 children articles and invert their order
 * - Favorite 2 different articles and invert their order in the favorite section
 */

import tour from 'web_tour.tour';

export const moveArticle = ($element, $target) => {
    const elementCenter = $element.offset();
    elementCenter.left += $element.outerWidth() / 2;
    elementCenter.top += $element.outerHeight() / 2;
    const targetCenter = $target.offset();
    targetCenter.left += $target.outerWidth() / 2;
    targetCenter.top += $target.outerHeight() / 2;
    const sign = Math.sign(targetCenter.top - elementCenter.top);
    // The mouse needs to be above (or below) the target depending on element
    // position (below (or above)) to consistently trigger the correct move.
    const offsetY = sign * $target.outerHeight() / 2;

    $element.trigger($.Event("mouseenter"));
    $element.trigger($.Event("mousedown", {
        which: 1,
        pageX: elementCenter.left,
        pageY: elementCenter.top,
    }));

    // The initial movement distance should be greater than the minimal movement
    // distance before the drag event starts on the (nested)sortable element
    $element.trigger($.Event("mousemove", {
        which: 1,
        pageX: elementCenter.left,
        pageY: elementCenter.top + sign * 11,
    }));

    // The timeout should be greater than the value of the delay before
    // the drag event starts on the (nested)sortable element
    setTimeout(() => {
        $element.trigger($.Event("mousemove", {
            which: 1,
            pageX: targetCenter.left,
            pageY: targetCenter.top + offsetY,
        }));

        $element.trigger($.Event("mouseup", {
            which: 1,
            pageX: targetCenter.left,
            pageY: targetCenter.top + offsetY,
        }));
    }, 151);
};

tour.register('knowledge_main_flow_tour', {
    test: true,
    url: '/web',
}, [tour.stepUtils.showAppsMenuItem(), {
    // open Knowledge App
    trigger: '.o_app[data-menu-xmlid="knowledge.knowledge_menu_root"]',
}, {
    // click on the main "Create" action
    trigger: '.o_knowledge_header .btn:contains("Create")',
}, {
    trigger: 'section[data-section="private"] .o_article .o_article_name:contains("Untitled")',
    run: () => {},  // check that the article is correctly created (private section)
}, {
    trigger: '.o_breadcrumb_article_name > input',
    run: 'text My Private Article',  // modify the article name
}, {
    trigger: '.note-editable.odoo-editor-editable',
    run: 'text Content of My Private Article',  // modify the article content
}, {
    trigger: 'section[data-section="workspace"]',
    run: () => {
        // force the create button to be visible (it's only visible on hover)
        $('section[data-section="workspace"] .o_section_create').css('visibility', 'visible');
    },
}, {
    // create an article in the "Workspace" section
    trigger: 'section[data-section="workspace"] .o_section_create',
}, {
    trigger: 'section[data-section="workspace"] .o_article .o_article_name:contains("Untitled")',
    run: () => {},  // check that the article is correctly created (workspace section)
}, {
    trigger: '.o_breadcrumb_article_name > input',
    run: 'text My Workspace Article',  // modify the article name
}, {
    trigger: '.note-editable.odoo-editor-editable',
    run: 'text Content of My Workspace Article',  // modify the article content
}, {
    trigger: '.o_article:contains("My Workspace Article")',
    run: () => {
        // force the create button to be visible (it's only visible on hover)
        $('.o_article:contains("My Workspace Article") button.o_article_create').css('visibility', 'visible');
    },
}, {
    // create child article
    trigger: '.o_article:contains("My Workspace Article") button.o_article_create',
}, {
    trigger: 'section[data-section="workspace"] .o_article .o_article_name:contains("Untitled")',
    run: () => {},  // check that the article is correctly created (workspace section)
}, {
    trigger: '.o_breadcrumb_article_name > input',
    run: 'text Child Article 1',  // modify the article name
}, {
    trigger: '.o_article:contains("My Workspace Article")',
    run: () => {
        // force the create button to be visible (it's only visible on hover)
        $('.o_article:contains("My Workspace Article") button.o_article_create').css('visibility', 'visible');
    },
}, {
    // create child article (2)
    trigger: '.o_article:contains("My Workspace Article") button.o_article_create',
}, {
    trigger: 'section[data-section="workspace"] .o_article .o_article_name:contains("Untitled")',
    run: () => {},  // check that the article is correctly created (workspace section)
}, {
    trigger: '.o_breadcrumb_article_name > input',
    run: 'text Child Article 2',  // modify the article name
}, {
    // move child article 2 above child article 1
    trigger: '.o_article_handle:contains("Child Article 2")',
    run: () => {
        moveArticle(
            $('.o_article_handle:contains("Child Article 2")'),
            $('.o_article_handle:contains("Child Article 1")'),
        );
    },
}, {
    // verify that the move was done
    trigger: '.o_article:has(.o_article_name:contains("My Workspace Article")) ul > :eq(0):contains("Child Article 2")',
    run: () => {},
}, {
    // go back to main workspace article
    trigger: 'section[data-section="workspace"] .o_article .o_article_name:contains("My Workspace Article")',
}, {
    trigger: '.o_knowledge_editor:contains("Content of My Workspace Article")',
    run: () => {},  // wait for article to be correctly loaded
}, {
    // open the share dropdown
    trigger: '.o_knowledge_header .btn:contains("Share")',
}, {
    // click on 'Invite'
    trigger: '.o_knowledge_share_panel .btn:contains("Invite")',
}, {
    // Type the invited person's name
    trigger: '.o_field_many2many_tags_email[name=partner_ids] input',
    run: 'text micheline@knowledge.com',
}, {
    // Create the partner
    trigger: '.ui-autocomplete.dropdown-menu a:contains("micheline@knowledge.com")',
    in_modal: false,
}, {
    // Submit the invite wizard
    trigger: 'button:contains("Invite")',
    extra_trigger: '.o_field_tags span.o_badge_text',
}, {
    // add to favorite
    trigger: '.o_toggle_favorite',
}, {
    // check article was correctly added into favorites
    trigger: 'section.o_favorite_container .o_article .o_article_name:contains("My Workspace Article")',
    run: () => {},
}, {
    // open the share dropdown
    trigger: '.o_knowledge_header .btn:contains("Share")',
}, {
    // open the share dropdown
    trigger: '.o_member_email:contains("micheline@knowledge.com")',
    in_modal: false,
    run: () => {},
}, {
    // go back to main workspace article
    trigger: 'section[data-section="private"] .o_article .o_article_name:contains("My Private Article")',
}, {
    trigger: '.o_knowledge_editor:contains("Content of My Private Article")',
    run: () => {},  // wait for article to be correctly loaded
}, {
    // add to favorite
    trigger: '.o_toggle_favorite',
}, {
    // wait for the article to be registered as favorited
    trigger: '.o_toggle_favorite .fa-star',
    run: () => {},
}, {
    // move private article above workspace article in the favorite section
    trigger: 'section.o_favorite_container .o_article_handle:contains("My Private Article")',
    run: () => {
        moveArticle(
            $('section.o_favorite_container .o_article_handle:contains("My Private Article")'),
            $('section.o_favorite_container .o_article_handle:contains("My Workspace Article")'),
        );
    },
}, {
    // verify that the move was done
    trigger: 'section.o_favorite_container ul > :eq(0):contains("My Private Article")',
    run: () => {},
}, {
    // go back to main workspace article
    trigger: 'section[data-section="workspace"] .o_article .o_article_name:contains("My Workspace Article")',
}, {
    trigger: ':contains("Content of My Workspace Article")',
    run() {},
}]);
