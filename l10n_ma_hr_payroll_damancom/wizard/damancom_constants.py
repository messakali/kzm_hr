# -*- coding: utf-8 -*-

SITUATION = [('NON_RENSEIGNE', 0), ('  ', 0), ('SO', 1), ('DE', 2),
             ('IT', 3), ('IL', 4), ('AT', 5), ('CS', 6), ('MS', 7), ('MP', 8)]

A00 = 'A00'
A01 = 'A01'
A02 = 'A02'
A03 = 'A03'

A00_L_Type_Enreg = 3
A00_N_Identif_Transfert = 14
A00_L_Cat = 2
A00_L_filler = 241

SPACE = ' '
ZERO = '0'

A01_L_Type_Enreg = 3
A01_N_Num_Affilie = 7
A01_L_Periode = 6
A01_L_Raison_Sociale = 40
A01_L_Activite = 40
A01_L_Adresse = 120
A01_L_Ville = 20
A01_C_Code_Postal = 6
A01_C_Code_Agence = 2
A01_D_Date_Emission = 8
A01_D_Date_Exig = 8

A02_L_Type_Enreg = 3
A02_N_Num_Affilie = 7
A02_L_Periode = 6
A02_N_Num_Assure = 9
A02_L_Nom_Prenom = 60
A02_N_Enfants = 2
A02_N_AF_A_Payer = 6
A02_N_AF_A_Deduire = 6
A02_N_AF_Net_A_Payer = 6
A02_L_filler = 155

A03_L_Type_Enreg = 3
A03_N_Num_Affilie = 7
A03_L_Periode = 6
A03_N_Nbr_Salaries = 6
A03_N_T_Enfants = 6
A03_N_T_AF_A_Payer = 12
A03_N_T_AF_A_Deduire = 12
A03_N_T_AF_Net_A_Payer = 12
A03_N_T_Num_Imma = 15
A03_L_filler = 181

B00_L_Type_Enreg = 3
B00_N_Identif_Transfert = 14
B00_L_Cat = 2
B00_L_filler = 241


B01_L_Type_Enreg = 3
B01_N_Num_Affilie = 7
B01_L_Periode = 6
B01_L_Raison_Sociale = 40
B01_L_Activite = 40
B01_L_Adresse = 120
B01_L_Ville = 20
B01_C_Code_Postal = 6
B01_C_Code_Agence = 2
B01_D_Date_Emission = 8
B01_D_Date_Exig = 8

B02_L_Type_Enreg = 3
B02_N_Num_Affilie = 7
B02_L_Periode = 6
B02_N_Num_Assure = 9
B02_L_Nom_Prenom = 60
B02_N_Enfants = 2
B02_N_AF_A_Payer = 6
B02_N_AF_A_Deduire = 6
B02_N_AF_Net_A_Payer = 6
B02_N_AF_A_Reverser = 6
B02_N_Jours_Declares = 2
B02_N_Salaire_Reel = 13
B02_N_Salaire_Plaf = 9
B02_L_Situation = 2
B02_S_Ctr = 19
B02_L_filler = 104


B03_L_Type_Enreg = 3
B03_N_Num_Affilie = 7
B03_L_Periode = 6
B03_N_Nbr_Salaries = 6
B03_N_T_Enfants = 6
B03_N_T_AF_A_Payer = 12
B03_N_T_AF_A_Deduire = 12
B03_N_T_AF_Net_A_Payer = 12
B03_N_T_Num_Imma = 15
B03_N_T_AF_A_Reverser = 12
B03_N_T_Jours_Declares = 6
B03_N_T_Salaire_Reel = 15
B03_N_T_Salaire_Plaf = 13
B03_N_T_Ctr = 19
B03_L_filler = 116

B04_L_Type_Enreg = 3
B04_N_Num_Affilie = 7
B04_L_Periode = 6
B04_N_Num_Assure = 9
B04_L_Nom_Prenom = 60
B04_L_Num_CIN = 8
B04_N_Nbr_Jours = 2
B04_N_Sal_Reel = 13
B04_N_Sal_Plaf = 9
B04_S_Ctr = 19
B04_L_filler = 124

B05_L_Type_Enreg = 3
B05_N_Num_Affilie = 7
B05_L_Periode = 6
B05_N_Nbr_Salaries = 6
B05_N_T_Num_Imma = 15
B05_N_T_Jours_Declares = 6
B05_N_T_Salaire_Reel = 15
B05_N_T_Salaire_Plaf = 13
B05_N_T_Ctr = 19
B05_L_filler = 170

B06_L_Type_Enreg = 3
B06_N_Num_Affilie = 7
B06_L_Periode = 6
B06_N_Nbr_Salaries = 6
B06_N_T_Num_Imma = 15
B06_N_T_Jours_Declares = 6
B06_N_T_Salaire_Reel = 15
B06_N_T_Salaire_Plaf = 13
B06_N_T_Ctr = 19
B06_L_filler = 170

LINE_MAX = 260


def get_standard_ch(ch, c, max, left=False):
    # FIUXME LEFT
    # SET CH to MAX length
    tmp = ''.join([c for x in range(LINE_MAX)])
    ch = str(ch)
    ch = ch.strip().upper()
    if len(ch) > max:
        return ch[:max]
    if len(ch) < max and left:
        tmp_left = ''.join([c for x in range(max - len(ch))])
        ch = tmp_left + ch
    tmp = ch + tmp
    return tmp[:max]


def get_situation_code(code):
    for line in SITUATION:
        if line[0] == code:
            return line[1]
    return 0


def get_a00(line):
    res = {}
    res['L_Type_Enreg'] = line[0:3]
    res['N_Identif_Transfert'] = line[3:17]
    res['L_Cat'] = line[17:19]
    res['L_filler'] = line[19:260]
    return res


def get_b00(line):
    res = {}
    res['L_Type_Enreg'] = line[0:3]
    res['N_Identif_Transfert'] = line[3:17]
    res['L_Cat'] = line[17:19]
    res['L_filler'] = line[19:260]
    return res


def set_b00(L_Type_Enreg, N_Identif_Transfert, L_Cat, L_filler):
    line = ""
    err = False
    if len(L_Type_Enreg) == B00_L_Type_Enreg:
        line += L_Type_Enreg
    else:
        err = True
    if len(N_Identif_Transfert) == B00_N_Identif_Transfert:
        line += N_Identif_Transfert
    else:
        err = True
    if len(L_Cat) == B00_L_Cat:
        line += L_Cat
    else:
        err = True
    if len(L_filler) == B00_L_filler:
        line += L_filler
    else:
        err = True
    return (err == False) and line or None


def get_a01(line):
    res = {}
    res['L_Type_Enreg'] = line[0:3]
    res['N_Num_Affilie'] = line[3:10]
    res['L_Periode'] = line[10:16]
    res['L_Raison_Sociale'] = line[16:56]
    res['L_Activite'] = line[56:96]
    res['L_Adresse'] = line[96:216]
    res['L_Ville'] = line[216:236]
    res['C_Code_Postal'] = line[236:242]
    res['C_Code_Agence'] = line[242:244]
    res['D_Date_Emission'] = line[244:252]
    res['D_Date_Exig'] = line[252:260]
    return res


def get_b01(line):
    res = {}
    res['L_Type_Enreg'] = line[0:3]
    res['N_Num_Affilie'] = line[3:10]
    res['L_Periode'] = line[10:16]
    res['L_Raison_Sociale'] = line[16:56]
    res['L_Activite'] = line[56:96]
    res['L_Adresse'] = line[96:216]
    res['L_Ville'] = line[216:236]
    res['C_Code_Postal'] = line[236:242]
    res['C_Code_Agence'] = line[242:244]
    res['D_Date_Emission'] = line[244:252]
    res['D_Date_Exig'] = line[252:260]
    return res


def set_b01(L_Type_Enreg, N_Num_Affilie, L_Periode, L_Raison_Sociale, L_Activite, L_Adresse, L_Ville, C_Code_Postal, C_Code_Agence, D_Date_Emission, D_Date_Exig):
    line = ""
    err = False
    if len(L_Type_Enreg) == B01_L_Type_Enreg:
        line += L_Type_Enreg
    else:
        err = True
    if len(N_Num_Affilie) == B01_N_Num_Affilie:
        line += N_Num_Affilie
    else:
        err = True
    if len(L_Periode) == B01_L_Periode:
        line += L_Periode
    else:
        err = True
    if len(L_Raison_Sociale) == B01_L_Raison_Sociale:
        line += L_Raison_Sociale
    else:
        err = True
    if len(L_Activite) == B01_L_Activite:
        line += L_Activite
    else:
        err = True
    if len(L_Adresse) == B01_L_Adresse:
        line += L_Adresse
    else:
        err = True
    if len(L_Ville) == B01_L_Ville:
        line += L_Ville
    else:
        err = True
    if len(C_Code_Postal) == B01_C_Code_Postal:
        line += C_Code_Postal
    else:
        err = True
    if len(C_Code_Agence) == B01_C_Code_Agence:
        line += C_Code_Agence
    else:
        err = True
    if len(D_Date_Emission) == B01_D_Date_Emission:
        line += D_Date_Emission
    else:
        err = True
    if len(D_Date_Exig) == B01_D_Date_Exig:
        line += D_Date_Exig
    else:
        err = True
    return (err == False) and line or None


def get_a02(line):
    res = {}
    res['L_Type_Enreg'] = line[0:3]
    res['N_Num_Affilie'] = line[3:10]
    res['L_Periode'] = line[10:16]
    res['N_Num_Assure'] = line[16:25]
    res['L_Nom_Prenom'] = line[25:85]
    res['N_Enfants'] = line[85:87]
    res['N_AF_A_Payer'] = line[87:93]
    res['N_AF_A_Deduire'] = line[93:99]
    res['N_AF_Net_A_Payer'] = line[99:105]
    res['L_filler'] = line[105:260]
    return res


def get_b02(line):
    res = {}
    res['L_Type_Enreg'] = line[0:3]
    res['N_Num_Affilie'] = line[3:10]
    res['L_Periode'] = line[10:16]
    res['N_Num_Assure'] = line[16:25]
    res['L_Nom_Prenom'] = line[25:85]
    res['N_Enfants'] = line[85:87]
    res['N_AF_A_Payer'] = line[87:93]
    res['N_AF_A_Deduire'] = line[93:99]
    res['N_AF_Net_A_Payer'] = line[99:105]
    res['N_AF_A_Reverser'] = line[105:111]
    res['N_Jours_Declares'] = line[111:113]
    res['N_Salaire_Reel'] = line[113:126]
    res['N_Salaire_Plaf'] = line[126:135]
    res['L_Situation'] = line[135:137]
    res['S_Ctr'] = line[137:156]
    res['L_filler'] = line[156:260]
    return res


def get_b03(line):
    res = {}
    res['L_Type_Enreg'] = line[0:3]
    res['N_Num_Affilie'] = line[3:10]
    res['L_Periode'] = line[10:16]
    res['N_Nbr_Salaries'] = line[16:22]
    res['N_T_Enfants'] = line[22:28]
    res['N_T_AF_A_Payer'] = line[28:40]
    res['N_T_AF_A_Deduire'] = line[40:52]
    res['N_T_AF_Net_A_Payer'] = line[52:64]
    res['N_T_Num_Imma'] = line[64:79]
    res['N_T_AF_A_Reverser'] = line[79:91]
    res['N_T_Jours_Declares'] = line[91:97]
    res['N_T_Salaire_Reel'] = line[97:112]
    res['N_T_Salaire_Plaf'] = line[112:125]
    res['N_T_Ctr'] = line[125:144]
    res['L_filler'] = line[144:260]
    return res


def get_b04(line):
    res = {}
    res['L_Type_Enreg'] = line[0:3]
    res['N_Num_Affilie'] = line[3:10]
    res['L_Periode'] = line[10:16]
    res['N_Num_Assure'] = line[16:25]
    res['L_Nom_Prenom'] = line[25:85]
    res['L_Num_CIN'] = line[85:93]
    res['N_Nbr_Jours'] = line[93:95]
    res['N_Sal_Reel'] = line[95:108]
    res['N_Sal_Plaf'] = line[108:117]
    res['S_Ctr'] = line[117:136]
    res['L_filler'] = line[136:260]
    return res


def get_b05(line):
    res = {}
    res['L_Type_Enreg'] = line[0:3]
    res['N_Num_Affilie'] = line[3:10]
    res['L_Periode'] = line[10:16]
    res['N_Nbr_Salaries'] = line[16:22]
    res['N_T_Num_Imma'] = line[22:37]
    res['N_T_Jours_Declares'] = line[37:43]
    res['N_T_Salaire_Reel'] = line[43:58]
    res['N_T_Salaire_Plaf'] = line[58:71]
    res['N_T_Ctr'] = line[71:90]
    res['L_filler'] = line[90:260]
    return res


def get_b06(line):
    res = {}
    res['L_Type_Enreg'] = line[0:3]
    res['N_Num_Affilie'] = line[3:10]
    res['L_Periode'] = line[10:16]
    res['N_Nbr_Salaries'] = line[16:22]
    res['N_T_Num_Imma'] = line[22:37]
    res['N_T_Jours_Declares'] = line[37:43]
    res['N_T_Salaire_Reel'] = line[43:58]
    res['N_T_Salaire_Plaf'] = line[58:71]
    res['N_T_Ctr'] = line[71:90]
    res['L_filler'] = line[90:260]
    return res


def set_b02(L_Type_Enreg, N_Num_Affilie, L_Periode, N_Num_Assure, L_Nom_Prenom, N_Enfants, N_AF_A_Payer, N_AF_A_Deduire, N_AF_Net_A_Payer, N_AF_A_Reverser, N_Jours_Declares, N_Salaire_Reel, N_Salaire_Plaf, L_Situation, S_Ctr, L_filler):
    line = ""
    err = False
    if len(L_Type_Enreg) == B02_L_Type_Enreg:
        line += L_Type_Enreg
    else:
        err = True
    if len(N_Num_Affilie) == B02_N_Num_Affilie:
        line += N_Num_Affilie
    else:
        err = True
    if len(L_Periode) == B02_L_Periode:
        line += L_Periode
    else:
        err = True
    if len(N_Num_Assure) == B02_N_Num_Assure:
        line += N_Num_Assure
    else:
        err = True
    if len(L_Nom_Prenom) == B02_L_Nom_Prenom:
        line += L_Nom_Prenom
    else:
        err = True
    if len(N_Enfants) == B02_N_Enfants:
        line += N_Enfants
    else:
        err = True
    if len(N_AF_A_Payer) == B02_N_AF_A_Payer:
        line += N_AF_A_Payer
    else:
        err = True
    if len(N_AF_A_Deduire) == B02_N_AF_A_Deduire:
        line += N_AF_A_Deduire
    else:
        err = True
    if len(N_AF_Net_A_Payer) == B02_N_AF_Net_A_Payer:
        line += N_AF_Net_A_Payer
    else:
        err = True
    if len(N_AF_A_Reverser) == B02_N_AF_A_Reverser:
        line += N_AF_A_Reverser
    else:
        err = True
    if len(N_Jours_Declares) == B02_N_Jours_Declares:
        line += N_Jours_Declares
    else:
        err = True
    if len(N_Salaire_Reel) == B02_N_Salaire_Reel:
        line += N_Salaire_Reel
    else:
        err = True
    if len(N_Salaire_Plaf) == B02_N_Salaire_Plaf:
        line += N_Salaire_Plaf
    else:
        err = True
    if len(L_Situation) == B02_L_Situation:
        line += L_Situation
    else:
        err = True
    if len(S_Ctr) == B02_S_Ctr:
        line += S_Ctr
    else:
        err = True
    if len(L_filler) == B02_L_filler:
        line += L_filler
    else:
        err = True
    return (err == False) and line or None


def get_a03(line):
    res = {}
    res['L_Type_Enreg'] = line[0:3]
    res['N_Num_Affilie'] = line[3:10]
    res['L_Periode'] = line[10:16]
    res['N_Nbr_Salaries'] = line[16:22]
    res['N_T_Enfants'] = line[22:28]
    res['N_T_AF_A_Payer'] = line[28:40]
    res['N_T_AF_A_Deduire'] = line[40:52]
    res['N_T_AF_Net_A_Payer'] = line[52:64]
    res['N_T_Num_Imma'] = line[64:79]
    res['L_filler'] = line[79:260]
    return res


def set_b03(L_Type_Enreg, N_Num_Affilie, L_Periode, N_Nbr_Salaries, N_T_Enfants, N_T_AF_A_Payer, N_T_AF_A_Deduire, N_T_AF_Net_A_Payer, N_T_Num_Imma, N_T_AF_A_Reverser, N_T_Jours_Declares, N_T_Salaire_Reel, N_T_Salaire_Plaf, N_T_Ctr, L_filler):
    line = ""
    err = False
    if len(L_Type_Enreg) == B03_L_Type_Enreg:
        line += L_Type_Enreg
    else:
        err = True
    if len(N_Num_Affilie) == B03_N_Num_Affilie:
        line += N_Num_Affilie
    else:
        err = True
    if len(L_Periode) == B03_L_Periode:
        line += L_Periode
    else:
        err = True
    if len(N_Nbr_Salaries) == B03_N_Nbr_Salaries:
        line += N_Nbr_Salaries
    else:
        err = True
    if len(N_T_Enfants) == B03_N_T_Enfants:
        line += N_T_Enfants
    else:
        err = True
    if len(N_T_AF_A_Payer) == B03_N_T_AF_A_Payer:
        line += N_T_AF_A_Payer
    else:
        err = True
    if len(N_T_AF_A_Deduire) == B03_N_T_AF_A_Deduire:
        line += N_T_AF_A_Deduire
    else:
        err = True
    if len(N_T_AF_Net_A_Payer) == B03_N_T_AF_Net_A_Payer:
        line += N_T_AF_Net_A_Payer
    else:
        err = True
    if len(N_T_Num_Imma) == B03_N_T_Num_Imma:
        line += N_T_Num_Imma
    else:
        err = True
    if len(N_T_AF_A_Reverser) == B03_N_T_AF_A_Reverser:
        line += N_T_AF_A_Reverser
    else:
        err = True
    if len(N_T_Jours_Declares) == B03_N_T_Jours_Declares:
        line += N_T_Jours_Declares
    else:
        err = True
    if len(N_T_Salaire_Reel) == B03_N_T_Salaire_Reel:
        line += N_T_Salaire_Reel
    else:
        err = True
    if len(N_T_Salaire_Plaf) == B03_N_T_Salaire_Plaf:
        line += N_T_Salaire_Plaf
    else:
        err = True
    if len(N_T_Ctr) == B03_N_T_Ctr:
        line += N_T_Ctr
    else:
        err = True
    if len(L_filler) == B03_L_filler:
        line += L_filler
    else:
        err = True
    return (err == False) and line or None


def set_b04(L_Type_Enreg, N_Num_Affilie, L_Periode, N_Num_Assure, L_Nom_Prenom, L_Num_CIN, N_Nbr_Jours, N_Sal_Reel, N_Sal_Plaf, S_Ctr, L_filler):
    line = ""
    err = False
    if len(L_Type_Enreg) == B04_L_Type_Enreg:
        line += L_Type_Enreg
    else:
        err = True
    if len(N_Num_Affilie) == B04_N_Num_Affilie:
        line += N_Num_Affilie
    else:
        err = True
    if len(L_Periode) == B04_L_Periode:
        line += L_Periode
    else:
        err = True
    if len(N_Num_Assure) == B04_N_Num_Assure:
        line += N_Num_Assure
    else:
        err = True
    if len(L_Nom_Prenom) == B04_L_Nom_Prenom:
        line += L_Nom_Prenom
    else:
        err = True
    if len(L_Num_CIN) == B04_L_Num_CIN:
        line += L_Num_CIN
    else:
        err = True
    if len(N_Nbr_Jours) == B04_N_Nbr_Jours:
        line += N_Nbr_Jours
    else:
        err = True
    if len(N_Sal_Reel) == B04_N_Sal_Reel:
        line += N_Sal_Reel
    else:
        err = True
    if len(N_Sal_Plaf) == B04_N_Sal_Plaf:
        line += N_Sal_Plaf
    else:
        err = True
    if len(S_Ctr) == B04_S_Ctr:
        line += S_Ctr
    else:
        err = True
    if len(L_filler) == B04_L_filler:
        line += L_filler
    else:
        err = True
    return (err == False) and line or None


def set_b05(L_Type_Enreg, N_Num_Affilie, L_Periode, N_Nbr_Salaries, N_T_Num_Imma, N_T_Jours_Declares, N_T_Salaire_Reel, N_T_Salaire_Plaf, N_T_Ctr, L_filler):
    line = ""
    err = False
    if len(L_Type_Enreg) == B05_L_Type_Enreg:
        line += L_Type_Enreg
    else:
        err = True
    if len(N_Num_Affilie) == B05_N_Num_Affilie:
        line += N_Num_Affilie
    else:
        err = True
    if len(L_Periode) == B05_L_Periode:
        line += L_Periode
    else:
        err = True
    if len(N_Nbr_Salaries) == B05_N_Nbr_Salaries:
        line += N_Nbr_Salaries
    else:
        err = True
    if len(N_T_Num_Imma) == B05_N_T_Num_Imma:
        line += N_T_Num_Imma
    else:
        err = True
    if len(N_T_Jours_Declares) == B05_N_T_Jours_Declares:
        line += N_T_Jours_Declares
    else:
        err = True
    if len(N_T_Salaire_Reel) == B05_N_T_Salaire_Reel:
        line += N_T_Salaire_Reel
    else:
        err = True
    if len(N_T_Salaire_Plaf) == B05_N_T_Salaire_Plaf:
        line += N_T_Salaire_Plaf
    else:
        err = True
    if len(N_T_Ctr) == B05_N_T_Ctr:
        line += N_T_Ctr
    else:
        err = True
    if len(L_filler) == B05_L_filler:
        line += L_filler
    else:
        err = True
    return (err == False) and line or None


def set_b06(L_Type_Enreg, N_Num_Affilie, L_Periode, N_Nbr_Salaries, N_T_Num_Imma, N_T_Jours_Declares, N_T_Salaire_Reel, N_T_Salaire_Plaf, N_T_Ctr, L_filler):
    line = ""
    err = False
    if len(L_Type_Enreg) == B06_L_Type_Enreg:
        line += L_Type_Enreg
    else:
        err = True
    if len(N_Num_Affilie) == B06_N_Num_Affilie:
        line += N_Num_Affilie
    else:
        err = True
    if len(L_Periode) == B06_L_Periode:
        line += L_Periode
    else:
        err = True
    if len(N_Nbr_Salaries) == B06_N_Nbr_Salaries:
        line += N_Nbr_Salaries
    else:
        err = True
    if len(N_T_Num_Imma) == B06_N_T_Num_Imma:
        line += N_T_Num_Imma
    else:
        err = True
    if len(N_T_Jours_Declares) == B06_N_T_Jours_Declares:
        line += N_T_Jours_Declares
    else:
        err = True
    if len(N_T_Salaire_Reel) == B06_N_T_Salaire_Reel:
        line += N_T_Salaire_Reel
    else:
        err = True
    if len(N_T_Salaire_Plaf) == B06_N_T_Salaire_Plaf:
        line += N_T_Salaire_Plaf
    else:
        err = True
    if len(N_T_Ctr) == B06_N_T_Ctr:
        line += N_T_Ctr
    else:
        err = True
    if len(L_filler) == B06_L_filler:
        line += L_filler
    else:
        err = True
    return (err == False) and line or None
