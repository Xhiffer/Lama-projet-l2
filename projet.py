# -*- coding: utf-8 -*-
"""
Created on Wed Oct 10 14:56:13 2018

@author: etudiant
"""

import csv
import matplotlib.pyplot as plt
import numpy as np


#on met toutes les notes sur le même coefficient
def memevaleur(l,l1):
    z=l[:]
    for i in range(len(l1)):#liste des UEs
        for n in range(len(l)):
            z[n][i]=(l[n][i]/float(l1[i]))*100
    return z
#on calcul la moyenne des personnes
def lmoyp(l):
    lmoyennepersonne=[]
    z=0
    for i in range(len(l)):
        for a in range(4):
            z= + l[i][a]
            if a ==3:
                lmoyennepersonne.append(z/4)
    return lmoyennepersonne
#calcul des moyennes par UEs


def moy(l):
    moyenneue=0
    for i in range(len(l)):
        moyenneue += l[i]
    moyenneue = moyenneue/len(l)
    return moyenneue

            
#On enleve les listes avec les coefficients
with open('donnees.txt', 'r') as f:
    reader = csv.reader(f)
    l= list(reader)
l1=l.pop(0)#supprime la première ligne de l et la stock dans l1 (coefs)
lf = []
for i in range(len(l)):
    lf.append([])
    for a in range(4):
        lf[-1].append(float(l[i][a])) # on convertit les str en float
lf = np.array(lf)   #on explique a lf que c'est du numpy

#calcul des moyennes par colonne
moyenne0 = moy(lf[:,0])
moyenne1 = moy(lf[:,1])
moyenne2 = moy(lf[:,2])
moyenne3 = moy(lf[:,3])
print(moyenne0,moyenne1,moyenne2,moyenne3)


#histogramme dela moyenne des ues avec les eleves
x = [lmoyp(lf)]
n, bins, patches = plt.hist(x, 50, facecolor='palevioletred', alpha=0.5)
plt.ylabel("nombre étudiants")
plt.xlabel('Moyenne')
plt.axis([0, 20,0,10])
plt.grid(True)
plt.annotate('moyenne', xy=(10,6))
plt.show()
plt.savefig("histo.pdf")
plt.close("all")

#création de liste avec les matieres
lc0= lf[:,0]
lc1=lf[:,1]
lc2=lf[:,2]
lc3=lf[:,3]

print(lc1)

#histo matière 0
x=lc0
n, bins, patches = plt.hist(x, bins = 50, range=(0,100),facecolor='crimson', alpha=0.5)
plt.ylabel("nombre étudiants")
plt.xlabel("note de la matière")
plt.grid(True)
plt.axvline(x=moyenne0, color='rosybrown', linestyle = '--')
plt.show()
plt.savefig("histomatiere1.pdf")
plt.close("all")

#histo matière 1

x=lc1
n, bins, patches = plt.hist(x, bins = 50, range=(0,100),facecolor='pink', alpha=0.5)
plt.ylabel("nombre étudiants")
plt.xlabel("note de la matière")
plt.grid(True)
plt.axvline(x=moyenne1, color='lightsalmon', linestyle = '--')
plt.show()
plt.savefig("histomatiere2.pdf")
plt.close("all")


#histo matière 2

x=lc2
n, bins, patches = plt.hist(x, bins = 50, range=(0,100),facecolor='lightpink', alpha=0.5)
plt.ylabel("nombre étudiants")
plt.xlabel("note de la matière")
plt.grid(True)
plt.axvline(x=moyenne2, color='mediumorchid', linestyle = '--')
plt.show()
plt.savefig("histomatiere3.pdf")
plt.close("all")


#histo matière 3
x=lc3
n, bins, patches = plt.hist(x, bins = 50, range=(0,100),facecolor='hotpink', alpha=0.5)
plt.ylabel("nombre étudiants")
plt.xlabel("note de la matière")
plt.grid(True)
plt.axvline(x=moyenne3, color='darkslateblue', linestyle = '--')
plt.show()
plt.savefig("histomatiere4.pdf")
plt.close("all")