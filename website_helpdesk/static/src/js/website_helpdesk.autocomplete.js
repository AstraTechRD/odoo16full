/** @odoo-module  */

import concurrency from 'web.concurrency';
import publicWidget from 'web.public.widget';

import { qweb } from 'web.core';

publicWidget.registry.knowledgeBaseAutocomplete = publicWidget.Widget.extend({
    selector: '.o_helpdesk_knowledge_search',
    events: {
        'input .search-query': '_onInput',
        'focusout': '_onFocusOut',
        'keydown .search-query': '_onKeydown',
    },

    init: function () {
        this._super.apply(this, arguments);

        this._dp = new concurrency.DropPrevious();

        this._onInput = _.debounce(this._onInput, 400);
        this._onFocusOut = _.debounce(this._onFocusOut, 100);
    },


    start: function () {
        this.$input = this.$('.search-query');
        this.$url = this.$el.data('ac-url');
        this.enabled = this.$el.data('autocomplete');

        return this._super.apply(this, arguments);
    },

    /**
     * @private
     */
    async _fetch() {
        const search = this.$input.val();
        if (!search || search.length < 3)
            return;

        const res = await this._rpc({
            route: this.$url,
            params: {
                'term': search,
            },
        });

        return res;
    },

    /**
     * @private
     */
    _render: function (res) {
        const $prevMenu = this.$menu;
        const search = this.$input.val();
        this.$el.toggleClass('dropdown show', !!res);
        if (!!res) {
            this.$menu = $(qweb.render('website_helpdesk.knowledge_base_autocomplete', {
                results: res.results,
                showMore: res.showMore,
                term: search,
            }));
            this.$el.append(this.$menu);
        }
        if ($prevMenu) {
            $prevMenu.remove();
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onInput: function () {
        if (!this.enabled)
            return;
        this._dp.add(this._fetch()).then(this._render.bind(this));
    },
    /**
     * @private
     */
    _onFocusOut: function () {
        if (!this.$el.has(document.activeElement).length) {
            this._render();
        }
    },
    /**
     * @private
     */
    _onKeydown: function (ev) {
        switch (ev.which) {
            case $.ui.keyCode.ESCAPE:
                this._render();
                break;
            case $.ui.keyCode.UP:
            case $.ui.keyCode.DOWN:
                ev.preventDefault();
                if (this.$menu) {
                    let $element = ev.which === $.ui.keyCode.UP ? this.$menu.children().last() : this.$menu.children().first();
                    $element.focus();
                }
                break;
        }
    },
});
