# from odoo.exceptions import ValidationError
# import base64

# def load_attendance(obj, file=False):
#     attendance_ids = False
#     if file:
#         try:
#             value = base64.decodestring(obj.file_path).replace("\"", '')
#             attendance_ids = value.split("\r\n")
#             l_index = 1
#             journal_log = ''
#         except Exception as e:
#             raise ValidationError(_(u'Fichier introuvale.'))