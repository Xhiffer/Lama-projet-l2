# -*- coding: utf-8 -*-
"""
Created on Wed Oct 10 14:56:13 2018

@author: etudiant
"""
"""
import csv

with open('données.txt', 'r') as f:
    reader = csv.reader(f)
    l= list(reader)
l.pop(0)
lf=l[:]
for i in range(len(l)):
    for a in range(5):
        lf[i][a]=float(l[i][a]) #mets les nombres en entier

"""




import csv

def memevaleur(l,l1):
    z=l[:]
    for i in range(len(l1)):#liste des UEs
        for n in range(len(l)):
            z[n][i]=(l[n][i]/float(l1[i]))*100
    return z
            

with open('données.txt', 'r') as f:
    reader = csv.reader(f)
    l= list(reader)
l1=l.pop(0)
l1.pop(-1)
lf=l[:]
for i in range(len(l)):
    for a in range(5):
        lf[i][a]=float(l[i][a])

        

#print(memevaleur(lf,l1))

def lmoyp(l):
    lmoyennepersonne=[]
    z=0
    for i in range(len(l)):
        for a in range(4):
            z= + l[i][a]
            if a ==3:
                lmoyennepersonne.append(z/4)
    return lmoyennepersonne
#print(lmoyp(l)) #calcul la moyenne de l'UE

import matplotlib.pyplot as plt

#plt.plot(lmoyp(l))
#plt.ylabel("moyenne des élèves")
#plt.show()
x = [lmoyp(l)]
n, bins, patches = plt.hist(x, 50, facecolor='palevioletred', alpha=0.5)
plt.ylabel("nombre étudiants")
plt.xlabel('Moyenne')
#plt.ylabel(u'élèves')
plt.axis([0, 20,0,10])
plt.grid(True)
plt.show()