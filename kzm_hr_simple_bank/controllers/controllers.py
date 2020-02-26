# -*- coding: utf-8 -*-
# from odoo import http


# class KzmHrSimpleBank(http.Controller):
#     @http.route('/kzm_hr_simple_bank/kzm_hr_simple_bank/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/kzm_hr_simple_bank/kzm_hr_simple_bank/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('kzm_hr_simple_bank.listing', {
#             'root': '/kzm_hr_simple_bank/kzm_hr_simple_bank',
#             'objects': http.request.env['kzm_hr_simple_bank.kzm_hr_simple_bank'].search([]),
#         })

#     @http.route('/kzm_hr_simple_bank/kzm_hr_simple_bank/objects/<model("kzm_hr_simple_bank.kzm_hr_simple_bank"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('kzm_hr_simple_bank.object', {
#             'object': obj
#         })
