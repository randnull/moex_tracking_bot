import codecs
f = codecs.open('data.txt', 'r', "utf_8_sig")
r = f.read()
r = r.split('MOEX Tracking Bot')
ans = []
for elem in r:
    s = elem.split()
    if len(s) > 5:
        time = s[1][1:] + ' ' + s[2][:-1]
        name = s[-22][:-1]
        ind1 = s[-4]
        ind2 = s[-1]
        price = s[-19]
        out = [time, name, price, ind1]
        ans.append(out)
d = dict()
d_val = {'BUY': 1, 'STRONG_BUY': 2, 'NEUTRAL': 0, 'SELL': -1, 'STRONG_SELL': -2}
money = 0
for elem in ans:
    price = elem[2]
    name = elem[1]
    ind1 = elem[3]
    b = d_val[ind1]
    money -= b * float(price)
    if name in d:
        d[name][0] += b 
        d[name][1] = float(price)
    else:
        d[name] = [b, float(price)]
    ret = elem + [str(b)] + [str(b * float(price))] + [str(money)]
    print('\t'.join(ret)) 

for name, elem in d.items():
    money += elem[0] * elem[1]
    ret = ['', name,  elem[1], '', elem[0], elem[0] * elem[1], money]
    print('\t'.join(map(str, ret))) 