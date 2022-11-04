# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo.addons.knowledge.tests.common import KnowledgeCommonWData
from odoo.tests.common import HttpCase
from odoo.tests.common import tagged, users, warmup


@tagged('knowledge_performance', 'post_install', '-at_install')
class KnowledgePerformanceHttpCase(KnowledgeCommonWData, HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.wkspace_grand_children = cls.env['knowledge.article'].create([{
            'name': 'Workspace Grand-Child',
            'parent_id': cls.workspace_children[0].id,
        }] * 2)

    @users('employee')
    @warmup
    def test_article_tree_panel(self):
        self.authenticate('employee', 'employee')
        with self.assertQueryCount(employee=15):
            data = self._prepare_json_rpc_data(
                active_article_id=self.wkspace_grand_children[0].id,
                unfolded_articles_ids=[self.article_shared.id],
            )

            self.url_open(
                "/knowledge/tree_panel",
                data=json.dumps(data).encode(),
                headers={"Content-Type": "application/json"},
            )

    @users('employee')
    @warmup
    def test_article_tree_panel_w_favorites(self):
        self.authenticate('employee', 'employee')

        self.env['knowledge.article.favorite'].create([{
            'user_id': self.env.user.id,
            'article_id': article_id
        } for article_id in (self.workspace_children | self.wkspace_grand_children).ids])

        with self.assertQueryCount(employee=16):
            data = self._prepare_json_rpc_data(
                active_article_id=self.wkspace_grand_children[0].id,
                unfolded_articles_ids=[self.article_shared.id],
            )
            self.url_open(
                "/knowledge/tree_panel",
                data=json.dumps(data).encode(),
                headers={"Content-Type": "application/json"},
            )

    def _prepare_json_rpc_data(self,
                               active_article_id=False,
                               unfolded_articles_ids=False,
                               unfolded_favorite_articles_ids=False):
        params = {}
        if active_article_id:
            params['active_article_id'] = active_article_id
        if unfolded_articles_ids:
            params['unfolded_articles_ids'] = unfolded_articles_ids
        if unfolded_favorite_articles_ids:
            params['unfolded_favorite_articles_ids'] = unfolded_favorite_articles_ids

        return {
            "id": 0,
            "jsonrpc": "2.0",
            "method": "call",
            "params": params
        }
