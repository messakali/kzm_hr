from odoo import api, fields, models, _
from odoo.exceptions import UserError

class ResCompany(models.Model):
    _inherit = 'res.company'
    
    url = fields.Char(string="Url serveur pointage")
    user = fields.Char(string="Utilisateur serveur pointage")
    bd = fields.Char(string="Base de données serveur pointage")
    login = fields.Char(string="Login")
    password = fields.Char(string="Mot de passe")