from odoo import tools
from odoo import api, fields, models


class sale_subscription_report(models.Model):
    _name = "sale.subscription.report"
    _description = "Subscription Analysis"
    _auto = False

    name = fields.Char()
    date_order = fields.Date('Order Date', readonly=True)
    end_date = fields.Date('End Date', readonly=True)
    product_id = fields.Many2one('product.product', 'Product', readonly=True)
    product_uom = fields.Many2one('uom.uom', 'Unit of Measure', readonly=True)
    recurring_monthly = fields.Float('Monthly Recurring Revenue', readonly=True)
    recurring_yearly = fields.Float('Yearly Recurring Revenue', readonly=True)
    recurring_total = fields.Float('Recurring Price', readonly=True)
    quantity = fields.Float('Quantity', readonly=True)
    partner_id = fields.Many2one('res.partner', 'Customer', readonly=True)
    user_id = fields.Many2one('res.users', 'Salesperson', readonly=True)
    team_id = fields.Many2one('crm.team', 'Sales Team', readonly=True)
    company_id = fields.Many2one('res.company', 'Company', readonly=True)
    categ_id = fields.Many2one('product.category', 'Product Category', readonly=True)
    pricelist_id = fields.Many2one('product.pricelist', 'Pricelist', readonly=True)
    template_id = fields.Many2one('sale.order.template', 'Subscription Template', readonly=True)
    product_tmpl_id = fields.Many2one('product.template', 'Product Template', readonly=True)
    country_id = fields.Many2one('res.country', 'Country', readonly=True)
    commercial_partner_id = fields.Many2one('res.partner', 'Customer Company', readonly=True)
    industry_id = fields.Many2one('res.partner.industry', 'Industry', readonly=True)
    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic Account', readonly=True)
    close_reason_id = fields.Many2one('sale.order.close.reason', 'Close Reason', readonly=True)
    to_renew = fields.Boolean('To Renew', readonly=True)
    stage_category = fields.Selection([
        ('draft', 'Draft'),
        ('progress', 'In Progress'),
        ('closed', 'Closed')], readonly=True)
    health = fields.Selection([
        ('normal', 'Neutral'),
        ('done', 'Good'),
        ('bad', 'Bad')], string="Health", readonly=True)
    stage_id = fields.Many2one('sale.order.stage', string='Stage', readonly=True)

    def _select(self):
        select_str = """
             SELECT min(l.id) as id,
                    sub.name as name,
                    l.product_id as product_id,
                    l.product_uom as product_uom,
                    sub.analytic_account_id as analytic_account_id,
                    sum(
                        coalesce(l.price_subtotal / nullif(sub.amount_untaxed, 0), 0)
                        * sub.recurring_monthly
                    ) as recurring_monthly,
                    sum(
                        coalesce(l.price_subtotal / nullif(sub.amount_untaxed, 0), 0)
                        * sub.recurring_monthly * 12
                    ) as recurring_yearly,
                    sum(l.price_subtotal) as recurring_total,
                    sum(l.product_uom_qty) as quantity,
                    sub.date_order as date_order,
                    sub.end_date as end_date,
                    sub.partner_id as partner_id,
                    sub.user_id as user_id,
                    sub.team_id,
                    sub.company_id as company_id,
                    sub.to_renew,
                    sub.stage_category,
                    sub.health,
                    sub.stage_id,
                    sub.sale_order_template_id as template_id,
                    t.categ_id as categ_id,
                    sub.pricelist_id as pricelist_id,
                    p.product_tmpl_id,
                    partner.country_id as country_id,
                    partner.commercial_partner_id as commercial_partner_id,
                    partner.industry_id as industry_id,
                    sub.close_reason_id as close_reason_id
        """
        return select_str

    def _from(self):
        from_str = """
                sale_order_line l
                      join sale_order sub on (l.order_id=sub.id)
                      join sale_order_stage stage on sub.stage_id = stage.id
                      left outer join account_analytic_account a on sub.id=a.id
                      join res_partner partner on sub.partner_id = partner.id
                        left join product_product p on (l.product_id=p.id)
                            left join product_template t on (p.product_tmpl_id=t.id)
                    left join uom_uom u on (u.id=l.product_uom)
        """
        return from_str

    def _where(self):
        return """
            WHERE sub.is_subscription is true
        """

    def _group_by(self):
        group_by_str = """
            GROUP BY l.product_id,
                    l.product_uom,
                    t.categ_id,
                    sub.analytic_account_id,
                    sub.recurring_monthly,
                    sub.amount_untaxed,
                    sub.date_order,
                    sub.end_date,
                    sub.partner_id,
                    sub.user_id,
                    sub.team_id,
                    sub.company_id,
                    sub.to_renew,
                    sub.stage_category,
                    sub.health,
                    sub.stage_id,
                    sub.name,
                    sub.sale_order_template_id,
                    sub.pricelist_id,
                    p.product_tmpl_id,
                    partner.country_id,
                    partner.commercial_partner_id,
                    partner.industry_id,
                    sub.close_reason_id
        """
        return group_by_str

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (
            %s
            FROM ( %s )
            %s
            %s
            )""" % (self._table, self._select(), self._from(), self._where(), self._group_by()))
