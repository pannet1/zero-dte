import pendulum as plum

now = plum.now()
fname = str(now.format('H')).zfill(2) + \
    str(now.format('m')).zfill(2) + \
    str(now.format('s')).zfill(2)
print(fname)
