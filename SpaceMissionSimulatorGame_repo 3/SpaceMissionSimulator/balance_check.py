"""Brute-force balance check: for every level, count affordable designs and how many survive
the deterministic physics checks (random events not included). Run: python balance_check.py"""
import itertools, sys
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from spacecraft import *
from physics import analyze, predicted_failures
from levels import LEVELS
for lv in LEVELS:
    tot=0; ok=0; best=None; reasons={}; inbud=0
    for combo in itertools.product(LV_SIZES,MATERIALS,SHIPS,SHIELDS,BOOSTERS,ENGINES,ENERGY,CARGO):
        if combo[2]=='station' or combo[7]=='multi': continue
        d=Design(dict(zip(DESIGN_KEYS,combo)))
        if lv.get('tutorial') and (d['engine'] not in('solid','liquid') ): continue
        a=analyze(d.c,lv)
        if not a['cargo_allowed'] or not a['cargo_fits']: continue
        c=d.total_cost()
        if c>lv['game']['budget']: continue
        inbud+=1
        f=predicted_failures(a)
        if f:
            reasons[f[0][0]]=reasons.get(f[0][0],0)+1
        else:
            ok+=1
            if best is None or c<best[0]: best=(c,combo,round(a['margin']))
    print(lv['id'],'inbudget',inbud,'viable',ok, 'pct %.1f'%(100*ok/max(1,inbud)),'cheapest',best)
    print('   ',reasons)
