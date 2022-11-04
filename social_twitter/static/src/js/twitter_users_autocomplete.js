/** @odoo-module */

import { CharField } from "@web/views/fields/char/char_field";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

import core from 'web.core';
const QWeb = core.qweb;

const { useEffect, useRef } = owl;

export class TwitterUsersAutocompleteField extends CharField {
    setup() {
        super.setup();

        this.orm = useService("orm");
        this.input = useRef('input');

        useEffect(() => {
            $(this.input.el).autocomplete({
                classes: {'ui-autocomplete': 'o_social_twitter_users_autocomplete'},
                source: async (request, response) => {
                    const accountId = this.props.record.data.account_id[0];
    
                    const suggestions = await this.orm.call(
                        'social.account',
                        'twitter_search_users',
                        [[accountId], request.term]
                    );
                    response(suggestions);
                },
                select: (ev, ui) => {
                    $(this.input.el).val(ui.item.name);
                    this.selectTwitterUser(ui.item);
                    ev.preventDefault();
                },
                html: true,
                minLength: 2,
                delay: 500,
            }).data('ui-autocomplete')._renderItem = function (ul, item){
                return $(QWeb.render('social_twitter.users_autocomplete_element', {
                    suggestion: item
                })).appendTo(ul);
            };
        });
    }

    async selectTwitterUser(twitterUser) {
        const twitterAccountId = await this.orm.call(
            'social.twitter.account',
            'create',
            [{
                name: twitterUser.name,
                twitter_id: twitterUser.id_str
            }]
        );

        await this.props.record.update({
            twitter_followed_account_id: [twitterAccountId, twitterUser.name]
        });
    }
}

registry.category("fields").add("twitter_users_autocomplete", TwitterUsersAutocompleteField);
