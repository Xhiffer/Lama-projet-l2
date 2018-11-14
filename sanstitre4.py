# -*- coding: utf-8 -*-
"""
Created on Wed Nov 14 15:03:22 2018

@author: etudiant
"""

+import numpy as np
import csv

with open('données.txt', 'r') as f:
    reader = csv.reader(f)
    l= list(reader)
l.pop(0)
lf=l[:]
for i in range(len(l)):
    for a in range(5):
        lf[i][a]=float(l[i][a])
print(np.array(lf))

def histoo(l):
    
    col1=np.array(l)[:,0]
    print(col1)
    plt.hist(col1)
    plt.xlabel("notes")
    plt.ylabel("n étudiants")
    plt.title('Nombre d\'étudiant en fonction des notes')
    plt.axvline(x=25, color= 'red', linestyle='--')

histoo(l)



def histo1(l):
    
    col1=np.array(l)[:,1]
    print(col1)
    plt.hist(col1)
    plt.xlabel("notes")
    plt.ylabel("n étudiants")
    plt.title('Nombre d\'étudiant en fonction des notes')
    plt.axvline(x=50, color= 'red', linestyle='--')
histo1(l)


def histo2(l):
    col1=np.array(l)[:,2]
    print(col1)
    plt.hist(col1)
    plt.xlabel("notes")
    plt.ylabel("n étudiants")
    plt.title('Nombre d\'étudiant en fonction des notes')
    plt.axvline(x=50, color= 'red', linestyle='--')
histo2(l)


def histo3(l):
    col1=np.array(l)[:,3]
    print(col1)
    plt.hist(col1)
    plt.xlabel("notes")
    plt.ylabel("n étudiants")
    plt.title('Nombre d\'étudiant en fonction des notes')
    plt.axvline(x=100, color= 'red', linestyle='--')
histo3(l)