# -*- coding: utf-8 -*-
"""
Created on Mon Oct 15 16:08:24 2018

@author: mathias.lunardi
"""
import numpy as np
l=[[34.0,39.0,75.0,23.0,1.0],[19.0,62.0,78.0,63.0,1.0],[22.0,50.0,71.0,32.0,1.0],[29.0,43.0,68.0,49.0,1.0],[30.0,61.0,75.0,51.0,1.0]]
"""
def moyen_classe (l):
for i in range (0):
    b=[0]
    print (b) 
    for a in range(len(l;-1):
        b[a]=b[a]+l[I]
        print(b)
        if a==len(l)-1 :
            b[a]=b[a]%len(l)
            print(b)
            return b         
""" 
import csv

with open('donnesprojet.txt', 'r') as f:
    reader = csv.reader(f)
    your_list = list(reader)
    print(your_list)
"""
lm=[]
l= np.array(l).astype(np.float)
somme_colone_1= sum( l[:,1])
somme_colone_1=somme_colone_1/5
lm.append(somme_colone_1)

l= np.array(l).astype(np.float)
somme_colone_2= sum( l[:,2])
somme_colone_2=somme_colone_2/5
lm.append(somme_colone_2)

l= np.array(l).astype(np.float)
somme_colone_3= sum( l[:,3])
somme_colone_3=somme_colone_3/5
lm.append(somme_colone_3)

l= np.array(l).astype(np.float)
somme_colone_4= sum( l[:,4])
somme_colone_4=somme_colone_4/5
lm.append(somme_colone_4)
print (lm)

"""