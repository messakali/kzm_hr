# -*- coding: utf-8 -*-

from openerp import models, fields, api, _
from dateutil.relativedelta import relativedelta
from openerp.exceptions import Warning as UserError

def fiscal_year_for(contract_date, current_date, n=0):
    if current_date < contract_date :
        raise UserError(_('La date %d doit être supérieur à %s' % (current_date, contract_date)))
    dt_start = fields.Date.from_string(contract_date)
#     print contract_date
#     print current_date
    dt_stop = dt_start + relativedelta(years=1, days=-1)
    dt_current = fields.Date.from_string(current_date)
    while True:
        if dt_current >= dt_start and dt_current <= dt_stop:
            return fields.Date.to_string(dt_start + relativedelta(years=n)), fields.Date.to_string(dt_stop + relativedelta(years=n))
        dt_start = dt_start +relativedelta(years=1)
        dt_stop = dt_stop +relativedelta(years=1)

def remove_accent(s):
    import unicodedata
    if isinstance(s, str):
        s = s.decode('utf8')
    return unicodedata.normalize('NFKD', s).encode('ascii', 'ignore')


def to_float(text):
    from openerp.tools.safe_eval import safe_eval as eval
    try:
        text = str(text).strip()
    except:
        pass
    if not text:
        return 0.0
    text = text.replace(',', '.').replace(';', '.').replace(' ', '')
    text = ''.join([x for x in text if x.isdigit() or x in ['.', '-', '+']])
    return float(eval(text))


def date_range(string):
    import calendar
    from datetime import datetime
    if isinstance(string, datetime):
        string = fields.Datetime.to_string(string)
    year, month = int(string[:4]), int(string[5:7])
    part1 = string[:8]
    day = str(calendar.monthrange(year, month)[1])
    return part1 + '01', part1 + day


def normalize(ch1, ch2):
    if not ch1 and not ch2:
        return ''
    if not ch1:
        return ch2
    if not ch2:
        return ch1
    if isinstance(ch1, str):
        ch1 = unicode(ch1, 'utf-8')
    if isinstance(ch2, str):
        ch2 = unicode(ch2, 'utf-8')
    if len(ch1) > len(ch2):
        return ch1
    ln = len(ch2)
    ch2 = ch2[:(len(ch2) - len(ch1)) / 2]
    res = ch2 + ch1 + ch2
    return res


def floattotime(value):
    if not value:
        return ''
    f = str(float(value)).split('.')
    n = int(f[0])
    m = float(f[1])
    m = m * 3. / 5
    m = int(m)
    return '{:0>2}:{:0<2}'.format(n, m)


def to_percent(value, is_tva=True):
    """
    @param : value (integer, float, long)
    @param : is_tva (default is TRue to retuen Ex if value = 0)
    return value %
    """
    assert isinstance(
        value, (int, long, float)), "This function accept numbers"
    value = "%f" % (value * 100)
    if is_tva and value == 0.0:
        return 'Ex'
    value = value.rstrip('0').rstrip('.')
    return str(value) + ' %'


def tradd(num):
    global t1, t2
    ch = ''
    if num == 0:
        ch = ''
    elif num < 20:
        ch = t1[num]
    elif num >= 20:
        if (num >= 70 and num <= 79)or(num >= 90):
            z = int(num / 10) - 1
        else:
            z = int(num / 10)
        ch = t2[z]
        num = num - z * 10
        if (num == 1 or num == 11) and z < 8:
            ch = ch + ' et'
        if num > 0:
            ch = ch + ' ' + tradd(num)
        else:
            ch = ch + tradd(num)
    return ch


def tradn(num):
    global t1, t2
    ch = ''
    flagcent = False
    if num >= 1000000000:
        z = int(num / 1000000000)
        ch = ch + tradn(z) + ' milliard'
        if z > 1:
            ch = ch + 's'
        num = num - z * 1000000000
    if num >= 1000000:
        z = int(num / 1000000)
        ch = ch + tradn(z) + ' million'
        if z > 1:
            ch = ch + 's'
        num = num - z * 1000000
    if num >= 1000:
        if num >= 100000:
            z = int(num / 100000)
            if z > 1:
                ch = ch + ' ' + tradd(z)
            ch = ch + ' cent'
            flagcent = True
            num = num - z * 100000
            if int(num / 1000) == 0 and z > 1:
                ch = ch + 's'
        if num >= 1000:
            z = int(num / 1000)
            if (z == 1 and flagcent) or z > 1:
                ch = ch + ' ' + tradd(z)
            num = num - z * 1000
        ch = ch + ' mille'
    if num >= 100:
        z = int(num / 100)
        if z > 1:
            ch = ch + ' ' + tradd(z)
        ch = ch + " cent"
        num = num - z * 100
        if num == 0 and z > 1:
            ch = ch + 's'
    if num > 0:
        ch = ch + " " + tradd(num)
    return ch


def trad(nb, unite, decim, custom, base):
    unites, decims = '',''
    if unite :
        unites = unite.lower().endswith('s') and unite or (unite + 's')
    if decim :
        decims = decim.lower().endswith('s') and decim or (decim + 's')
    global t1, t2
    nb = round(nb, 2)
    t1 = ["", "un", "deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf", "dix",
          "onze", "douze", "treize", "quatorze", "quinze", "seize", "dix-sept", "dix-huit", "dix-neuf"]
    t2 = ["", "dix", "vingt", "trente", "quarante", "cinquante",
          "soixante", "septante", "quatre-vingt", "nonante"]
    z1 = int(nb)
    z3 = ((nb - z1) * 100) * base/100.
    z2 = int(round(z3, 0))
    demi = custom and str(z2).startswith('5') and str(z2).replace('0','') == '5' and True or False
    if z1 == 0:
        ch = u"zéro"
    else:
        ch = tradn(abs(z1))
    if z1 > 1 or z1 < -1:
        if unite != '':
            ch = ch + " " + unites
    else:
        ch = ch + " " + unite
    if z2 > 0:
        if demi :
            ch = ch + " et demi"
        else:
            ch = ch + tradn(z2)
        if z2 > 1 or z2 < -1:
            if decim != '' and not demi:
                ch = ch + " " + decims
        else:
            if not demi :
                ch = ch + " " + decim
    if nb < 0:
        ch = "moins " + ch
    return ch


def convert_txt2amount(nb, unite="DH", decim="centime", custom=False, base=100):
    return trad(nb, unite, decim, custom, base).strip().capitalize()
