# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_sale.controllers.main import WebsiteSale


class WebsiteSaleRenting(WebsiteSale):

    def _get_search_options(self, **post):
        options = super()._get_search_options(**post)
        options.update({
            'from_date': post.get('start_date'),
            'to_date': post.get('end_date'),
            'rent_only': post.get('rent_only') in ('True', 'true', '1'),
        })
        return options

    def _shop_get_query_url_kwargs(self, category, search, min_price, max_price, **post):
        result = super()._shop_get_query_url_kwargs(category, search, min_price, max_price, **post)
        result.update(
            start_date=post.get('start_date'),
            end_date=post.get('end_date'),
        )
        return result

    def _product_get_query_url_kwargs(self, category, search, **kwargs):
        result = super()._product_get_query_url_kwargs(category, search, **kwargs)
        result.update(
            start_date=kwargs.get('start_date'),
            end_date=kwargs.get('end_date'),
        )
        return result
