# -*- coding: utf-8 -*-


from openerp.tests.common import TransactionCase
import time


class Sequence(TransactionCase):

    def setUp(self):
        super(Sequence, self).setUp()
        self.sequence_model = self.registry('ir.sequence')

    def test_seq(self):
        cr, uid = self.cr, self.uid
        seq_id = self.sequence_model.create(cr, uid, {
            'name': 'year2',
            'prefix': 'F%(year2)s',
        })
        val = 'F' + time.strftime('%Y')[2:4]
        result = self.sequence_model._next(cr, uid, [seq_id])
        result = result[:3]
        self.assertEqual(
            val, result, "The result [%s] should be [%s]" % (result, val,))
