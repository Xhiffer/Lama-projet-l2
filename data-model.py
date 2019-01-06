# -*- coding: utf-8 -*-
"""
Created on Wed Sep 26 16:39:49 2018

@author: matth
"""
#Data model python
# =============================================================================
# # à tout les fonction "lib." voirs la Library.py pour plus d'info
# =============================================================================
import csv
import Library as lib

lib.my_mkdir('/Users/matth/Desktop/Logiciel Cool/programme-py/notes-élèves') 

with open('données.txt', 'r') as f:
    reader = csv.reader(f)# lis le document txt telquel
    l= list(reader) #crée une liste depuis le document données.txt
l.pop(0) #supprime la 1ère liste qui exprime les notes max de chaque matière
lf=l.copy() #lf = à une copie de la liste l


with open('prénom.txt', 'r') as name:
    reader = csv.reader(name) # lis le document txt telquel
    # je supose que le programme comprend en compte les retours à la ligne comme des virgules 
    lname= list(reader) #crée une liste depuis le document prénom.txt


lm= lib.allfloat(lf)
lm=lib.names(lm,lname)
print("1")

lib.graph(lm)
print("2")

lib.gen_pdf(lm)
if __name__ == '__main__': #je savais à quoi ça sert mais je sais plus [à revoir]
    lib.gen_pdf(lm)
print("TADA!")
print(lib.globaltime)

