# -*- coding: utf-8 -*-

from odoo import api, fields, models

import base64


class EBds(models.TransientModel):
    _name = 'e_bds'

    period_id = fields.Many2one('date.range', string=u'Période',
                                domain="[('type_id.fiscal_period', '=', True)]",  required=True)
    file_import = fields.Binary(string=u'Fichier préétabli')
    file_export = fields.Binary(string=u'Fichier e-BDS', readonly=True)
    name = fields.Char('Filename', readonly=True)
    state = fields.Selection(selection=(('choose', 'choose'), ('get', 'get')), default='choose' )

    @api.multi
    def generate(self):
        bultain_salaire = self.env['hr.payroll_ma.bulletin']
        e_bds_sortant = self.env['e_bds.sortant']
        e_bds_sortant_line = self.env['e_bds.sortant.line']

        for rec in self:
            e_bds_sortant_id = e_bds_sortant.search([('name', '=', rec.period_id.id)], limit=1)

            file_content_decoded = base64.decodestring(rec.file_import)
            data = file_content_decoded.split('\n')
            output = ''

            l1 = data[0]
            l1 = 'B'+ l1[1:17]+'B'+l1[18:]
            output += l1 + '\n'

            l2 = data[1]
            l2 = 'B' + l2[1:]
            num_affilie = l2[3:10]
            periode_dec = l2[10:16]
            Nom_fichier = 'DS_' + num_affilie + '_'+periode_dec+'.txt'
            output += l2 + '\n'

            nombre_salaries = 0
            total_matriculation = 0
            total_working_days = 0
            total_salaire_reel = 0
            total_N_SALAIRE_Plaf = 0
            total_S_CTR = 0
            for emp in data[2:-2]:
                salaire_reel = 0
                N_SALAIRE_Plaf = ''
                S_CTR = ''
                bultain_id = bultain_salaire.search([('employee_id.ssnid', '=', emp[16:25]),
                                                     ('period_id', '=', rec.period_id.id)])

                if bultain_id:
                    bultain_id[0].normal = True
                    nombre_salaries += 1
                    total_matriculation += int(emp[16:25])
                    salaire_reel = bultain_id[0].salaire_brute_imposable
                    working_days = bultain_id[0].working_days
                    total_working_days += int(working_days)

                    salaire_reel_str = str(int(salaire_reel*100)).replace('.', '').rjust(13,'0')
                    total_salaire_reel += int(salaire_reel*100)

                    working_days = str(working_days)[:2].replace('.', '')
                    sal_plaf = 0
                    N_AF_A_REVERSER = "".rjust(6,'0')
                    if salaire_reel < 6000:
                        sal_plaf = int(salaire_reel*100)
                    else:
                        sal_plaf = 600000

                    N_SALAIRE_Plaf = str(sal_plaf).replace('.', '').rjust(9,'0')
                    total_N_SALAIRE_Plaf += int(sal_plaf)
                    #Calcul de situation
                    L_situation = ''
                    situation_chiffre = 0

                    if e_bds_sortant_id:
                        e_bds_sortant_line_id = e_bds_sortant_line.search([('e_bds_sortant_id', '=', e_bds_sortant_id.id),
                                                                          ('employee_id.ssnid', '=', emp[16:25])], limit=1)
                        if e_bds_sortant_line_id:
                            L_situation = e_bds_sortant_line_id.situation
                            if L_situation == 'SO':
                                situation_chiffre = 1
                            elif L_situation == 'DE':
                                situation_chiffre = 2
                            elif L_situation == 'IT':
                                situation_chiffre = 3
                            elif L_situation == 'IL':
                                situation_chiffre = 4
                            elif L_situation == 'AT':
                                situation_chiffre = 5
                            elif L_situation == 'CS':
                                situation_chiffre = 6
                            elif L_situation == 'MS':
                                situation_chiffre = 7
                            else:
                                situation_chiffre = 8

                    L_situation=L_situation.rjust(2)
                    S_CTR=str (int(salaire_reel*100)+int(emp[16:25])+int(N_SALAIRE_Plaf)+int(working_days) +situation_chiffre)

                    total_S_CTR += int(S_CTR.replace('.', ''))

                    L_filter = "".rjust(104)

                    salaire_pre =""
                    salaire_pre = "B02"+ emp[3:105]+N_AF_A_REVERSER+working_days.rjust(2,'0')+salaire_reel_str+N_SALAIRE_Plaf+L_situation+S_CTR.replace('.', '').rjust(19,'0')+L_filter
                    output+=salaire_pre + '\n'
                #Sortants:
                else:
                    S_CTR_sortant = 0
                    if e_bds_sortant_id:
                        e_bds_sortant_line_id = e_bds_sortant_line.search([('e_bds_sortant_id', '=', e_bds_sortant_id.id),
                                                                          ('employee_id.ssnid', '=', emp[16:25])], limit=1)
                        if e_bds_sortant_line_id:
                            nombre_salaries += 1
                            total_matriculation += int(emp[16:25])
                            situation = e_bds_sortant_line_id.situation
                            if situation == 'SO':
                                S_CTR_sortant = 1
                            elif situation == 'DE':
                                S_CTR_sortant = 2
                            elif situation == 'IT':
                                S_CTR_sortant = 3
                            elif situation == 'IL':
                                S_CTR_sortant = 4
                            elif situation == 'AT':
                                S_CTR_sortant = 5
                            elif situation == 'CS':
                                S_CTR_sortant = 6
                            elif situation == 'MS':
                                S_CTR_sortant = 7
                            else:
                                S_CTR_sortant = 8

                            S_CTR = str (int(emp[16:25])+S_CTR_sortant)
                            total_S_CTR += int(S_CTR)
                            S_CTR_sortant = str(S_CTR).rjust(19,'0')

                            salaire_sortant=""
                            salaire_sortant = "B02" + emp[3:105]+"".rjust(30,'0')+situation+S_CTR_sortant+"".rjust(104)
                            output+=salaire_sortant + '\n'
            NT1 = "".rjust(42,'0')

            B03 = "B03"+l2[3:16]+str(nombre_salaries).rjust(6,'0')+NT1+str(total_matriculation).rjust(15,'0')+"".rjust(12,'0')+str(total_working_days).rjust(6,'0')+str(total_salaire_reel).rjust(15,'0')+str(total_N_SALAIRE_Plaf).rjust(13,'0')+str(total_S_CTR).rjust(19,'0')+"".rjust(116)
            output+=B03+'\n'
            #Entrants
            bultain_ids = bultain_salaire.search([('normal', '=', False),('period_id', '=', rec.period_id.id)])
            N_Nbr_Salaries_entrants = 0
            N_T_Num_Imma_entrants = 0
            N_T_Jours_Declare_entrants = 0
            N_T_Salaire_Reel_entrants = 0
            N_T_Salaire_Plaf_entrants = 0
            N_T_Ctr_entrants = 0
            for entrant in bultain_ids:
                salaire_entrant = ""
                N_Num_Assure = entrant.employee_id.ssnid
                L_Nom_nom = entrant.employee_id.name
                L_Nom_prenom = entrant.employee_id.prenom
                L_Num_CIN = entrant.employee_id.cin
                N_Nbr_Jours = int(str(entrant.working_days).replace('.', '')[:-1])
                N_Sal_Reel = int(entrant.salaire_brute_imposable*100)
                N_Sal_Plaf = 0
                if N_Sal_Reel < 600000:
                    N_Sal_Plaf = N_Sal_Reel
                else:
                    N_Sal_Plaf = 600000

                if not N_Num_Assure:
                    N_Num_Assure = '0'
                S_Ctr = int(N_Num_Assure)+N_Nbr_Jours+N_Sal_Reel+N_Sal_Plaf

                N_Nbr_Salaries_entrants += 1
                N_T_Num_Imma_entrants +=int(N_Num_Assure)
                N_T_Jours_Declare_entrants += N_Nbr_Jours
                N_T_Salaire_Reel_entrants += N_Sal_Reel
                N_T_Salaire_Plaf_entrants += N_Sal_Plaf
                N_T_Ctr_entrants += S_Ctr

                salaire_entrant = "B04"+l2[3:16]+str(N_Num_Assure).rjust(9,'0')+str(L_Nom_nom).ljust(30)+str(L_Nom_prenom).ljust(30)+str(L_Num_CIN).rjust(8," ")+str(N_Nbr_Jours).rjust(2,'0')+str(N_Sal_Reel).rjust(13,'0')+str(N_Sal_Plaf).rjust(9,'0')+str(S_Ctr).rjust(19,'0')+"".rjust(124)
                output+=salaire_entrant+'\n'

            if not bultain_ids:
                salaire_entrant = "B04"+l2[3:16]+''.rjust(9)+str('').rjust(60)+str('').rjust(8," ")+str(0).rjust(2,'0')+str(0).rjust(13,'0')+str(0).rjust(9,'0')+str(0).rjust(19,'0')+"".rjust(124)
                output += salaire_entrant+'\n'

            B05 = "B05"+l2[3:16]+str(N_Nbr_Salaries_entrants).rjust(6,'0')+str(N_T_Num_Imma_entrants).rjust(15,'0')+str(N_T_Jours_Declare_entrants).rjust(6,'0')+str(N_T_Salaire_Reel_entrants).rjust(15,'0')+str(N_T_Salaire_Plaf_entrants).rjust(13,'0')+str(N_T_Ctr_entrants).rjust(19,'0')+"".rjust(170)
            output += B05+'\n'

            N_Nbr_Salaries = nombre_salaries+N_Nbr_Salaries_entrants
            N_T_Num_Imma = total_matriculation+N_T_Num_Imma_entrants
            N_T_Jours_Declares = N_T_Jours_Declare_entrants+total_working_days
            N_T_Salaire_Reel = total_salaire_reel+N_T_Salaire_Reel_entrants
            N_T_Salaire_Plaf = N_T_Salaire_Plaf_entrants+total_N_SALAIRE_Plaf
            N_T_Ctr = total_S_CTR+N_T_Ctr_entrants
            B06 = "B06"+l2[3:16]+str(N_Nbr_Salaries).rjust(6,'0')+str(N_T_Num_Imma).rjust(15,'0')+str(N_T_Jours_Declares).rjust(6,'0')+str(N_T_Salaire_Reel).rjust(15,'0')+str(N_T_Salaire_Plaf).rjust(13,'0')+str(N_T_Ctr).rjust(19,'0')+"".rjust(170)
            output += B06+'\n'
            out = base64.encodestring(output)
            rec.state = 'get'
            rec.file_export = out
            rec.name = Nom_fichier
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'e_bds',
                'view_mode': 'form',
                'view_type': 'form',
                'res_id': rec.id,
                'views': [(False, 'form')],
                'target': 'new',
            }
