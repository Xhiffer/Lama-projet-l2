# -*- coding: utf-8 -*-
"""
Created on Wed Oct 10 18:14:33 2018

@author: matth
"""

import csv
with open('données.txt', 'r') as f:
    reader = csv.reader(f)
    l= list(reader)
l.pop(0)
lf=l[:]
for i in range(len(l)):
    for a in range(5):
        lf[i][a]=float(l[i][a])


def mêmevaleur(lf):
    a=lf[:]
    for i in range (len(l)):
        a[i][0]= (l[i][0])*2
        a[i][3]=(l[i][3])/2
    return a

lft=mêmevaleur(lf)

def lmoyp(lft):
    lmoyennepersonne=[]
    
    for i in range(len(l)):
        z=0
        for a in range(4):
            z= z+ l[i][a]
            if a ==3:
                lmoyennepersonne.append(z/4)
    return lmoyennepersonne
print(lmoyp(lft))


