# -*- coding: utf-8 -*-
# from odoo import http


# class KzmSimpleAddress(http.Controller):
#     @http.route('/kzm_simple_address/kzm_simple_address/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/kzm_simple_address/kzm_simple_address/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('kzm_simple_address.listing', {
#             'root': '/kzm_simple_address/kzm_simple_address',
#             'objects': http.request.env['kzm_simple_address.kzm_simple_address'].search([]),
#         })

#     @http.route('/kzm_simple_address/kzm_simple_address/objects/<model("kzm_simple_address.kzm_simple_address"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('kzm_simple_address.object', {
#             'object': obj
#         })
