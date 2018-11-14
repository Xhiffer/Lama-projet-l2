# -*- coding: utf-8 -*-
"""
Created on Mon Oct 15 14:29:32 2018

@author: etudiant
"""

import numpy as np #nombre
import csv #import de bases de données 
import matplotlib.pyplot as plt #pour faire des graphes/courbes



def histo(col,arange,bins,color,x,title):
    

    #print(col)
    plt.hist(col, range=arange, bins= bins, color= color, edgecolor='white')
    
    plt.xlabel("notes")
    plt.ylabel("n étudiants")
    plt.title(title)
   # plt.title('Nombre d\'étudiant en fonction des notes')
    plt.axvline(x=x, color= 'red', linestyle='--')




with open('données.txt', 'r') as f:
    reader = csv.reader(f)
    l= list(reader)
l.pop(0)
lf=l[:]
for i in range(len(l)):
    for a in range(5):
        lf[i][a]=float(l[i][a])
print(np.array(lf))


#histo(l)
#histo1(l)
#histo2(l)
histo(np.array(l)[:,0],(5,56),12,'blue',25,'col0')
plt.savefig('col0.pdf')
plt.close('all')


histo(np.array(l)[:,1],(22,94),20,'orange',50,'col1')
plt.savefig('col1.pdf')
plt.close('all')


histo(np.array(l)[:,2],(27.5,94),20,'green',50,'col2')
plt.savefig('col2.pdf')
plt.close('all')


histo(np.array(l)[:,3],(6,77),12,'yellow',100,'col3')
plt.savefig('col3.pdf')
plt.close('all')


