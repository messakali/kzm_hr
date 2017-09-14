# encoding: utf-8

from odoo import models, fields, api, _
from odoo.exceptions import Warning


class hr_employee_warning(models.Model):
    _name = 'hr.employee.warning'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _description = 'Avertissements'
    _order = 'action_date desc'
    _rec_name = 'effet'

    employee_id = fields.Many2one(
        'hr.employee', string=u'Employé',  required=True, default=lambda self: self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1),)
    action_date = fields.Date(string=u'Date d\'effet',  required=True, )
    edition_date = fields.Date(
        string=u'Date d\'édition',  required=True, default=lambda self: fields.Date.today(),)
    city = fields.Char(
        string=u'Ville', size=64, default=lambda self: self.env.user.company_id.city, required=True, )

    effet = fields.Text(string=u'Effet', required=True,)

    type_id = fields.Many2one(
        'hr.employee.warning.type', string=u'Type d\'avertissement',  required=True, )
    notes = fields.Text(string=u'Notes',)
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('sent', 'Envoyé'),
        ('received', 'Reçu'),
        ('cancel', 'Annulé'),
    ], string=u'État', readonly=True, track_visibility='onchange', copy=False, default='draft',)

    @api.model
    def set_sent(self):
        self.state = 'sent'

    @api.model
    def set_draft(self):
        self.state = 'draft'

    @api.model
    def set_received(self):
        self.state = 'received'

    @api.model
    def set_cancel(self):
        self.state = 'cancel'

    @api.multi
    def unlink(self):
        for obj in self:
            if obj.state != 'draft':
                raise Warning(
                    _('Vous ne pouvez pas supprimer un document qui n\'est pas en état brouillon'))
        return super(hr_employee_warning, self).unlink()

    @api.multi
    def action_print(self):
        return self.env['report'].get_action(self, 'kzm_hr_doc.report_warning')


class hr_employee_warning_type(models.Model):
    _name = 'hr.employee.warning.type'
    _description = 'Type d\'avertissement'

    name = fields.Char(string=u'Nom', size=64,  required=True, )
    objet = fields.Text(string=u'Objet', required=True,)

    line_before_ids = fields.One2many(
        'hr.employee.warning.type.line', 'type_before_id', string=u'Lignes d\'avant',)

    line_after_ids = fields.One2many(
        'hr.employee.warning.type.line', 'type_after_id', string=u'Lignes d\'après',)


class hr_employee_warning_type_line(models.Model):
    _name = 'hr.employee.warning.type.line'
    _description = 'Lignes des type des avertissements'
    _order = 'sequence asc'

    sequence = fields.Integer(string=u'Séquence', default=1,)
    name = fields.Text(string=u'Article', required=True,)
    type_before_id = fields.Many2one(
        'hr.employee.warning.type', string=u'Type',)
    type_after_id = fields.Many2one('hr.employee.warning.type', string=u'Type',)
