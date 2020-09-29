from odoo import _, api, exceptions, fields, models, tools

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    url = fields.Char(related='company_id.url', string="Url serveur pointage", readonly=False)
    user = fields.Char(related='company_id.user', string="Utilisateur serveur pointage", readonly=False)
    bd = fields.Char(related='company_id.bd', string="Base de données serveur pointage", readonly=False)
    login = fields.Char(related='company_id.login', string="Login", readonly=False)
    password = fields.Char(related='company_id.password', string="Mot de passe", readonly=False)


    def set_config_pointeuse(self):
        data = {
            'url':self.url,
            'user':self.user,
            'bd':self.bd,
            'login':self.login,
            'password':self.password
        }
        return data