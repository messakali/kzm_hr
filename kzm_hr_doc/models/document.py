# encoding: utf-8

from odoo import models, fields, api, _
from odoo.exceptions import Warning

class hr_document_type(models.Model):
    _name = 'hr.document.type'
    _description = 'Types des documents'
    _order = 'name asc'

    name = fields.Char(string=u'Nom', size=64, required=True,)
    can_request = fields.Boolean(string=u'Peut être demandé', default=True)


class hr_document(models.Model):
    _name = 'hr.document'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _description = 'Documents'

    name = fields.Char(string=u'Nom', size=64, required=True,)
    type_id = fields.Many2one(
        'hr.document.type', string=u'Type', required=True,)
    date = fields.Date(
        string=u'Date', required=True, default=lambda self: fields.Date.today(),)
    employee_id = fields.Many2one(
        'hr.employee', string=u'Employé', required=False,)
    user_id = fields.Many2one(
        'res.users',
        string=u'Utilisateur',
        required=True,
        default=lambda self: self.env.user,
        readonly=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string=u'Société',
        required=True,
        default=lambda self: self.env.user.company_id,
        readonly=True,
    )

    notes = fields.Text(string=u'Description',)
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirm', 'Confirmée'),
        ('ready', 'Prêt'),
        ('delivered', 'Livré'),
        ('cancel', 'Annulée'),
    ], string=u'État', readonly=True, track_visibility='onchange', copy=False, default='draft',)

    @api.model
    def set_confirm(self):
        for record in self:
            user_ids = []
            if record.user_id :
                user_ids += [record.user_id.id]
            record.message_subscribe_users(user_ids=user_ids)
        self.message_post(_("En atente de préparation du document."))
        self.state = 'confirm'

    @api.model
    def set_draft(self):
        self.state = 'draft'

    @api.model
    def set_ready(self):
        self.message_post(_("Le document est prêt."))
        self.state = 'ready'

    @api.model
    def set_delivered(self):
        self.message_post(_("Document est livré."))
        self.state = 'delivered'

    @api.model
    def set_cancel(self):
        self.message_post(_("Demande refusée."))
        self.state = 'cancel'

    @api.multi
    def unlink(self):
        for obj in self:
            if obj.state != 'draft':
                raise Warning(
                    _('Vous ne pouvez pas supprimer un document qui n\'est pas en état brouillon'))
        return super(hr_document, self).unlink()
