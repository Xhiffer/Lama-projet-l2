# -*- coding: utf-8 -*-
"""
Created on Wed Oct 10 14:56:13 2018

@author: etudiant
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




def lmoyp(l):
    lmoyennepersonne=[]
    z=0
    for i in range(len(l)):
        for a in range(4):
            z= + l[i][a]
            if a ==3:
                lmoyennepersonne.append(z/5)
    return lmoyennepersonne
print(lmoyp(l))

def mêmevaleur(l):
    a=[]
    
    for i in range (len(l)):
        a= l[i]*2