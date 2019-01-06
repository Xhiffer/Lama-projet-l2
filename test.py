# -*- coding: utf-8 -*-
"""
Created on Fri Jan  4 15:19:33 2019

@author: matth
"""
import matplotlib.pyplot as plt
import numpy as np 
import csv
from random import randint
import os
import errno
from io import BytesIO
from PyPDF2 import PdfFileWriter, PdfFileReader
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A3



@memevaleur
def allfloat(lf):
     for i in range(len(lf)):
        for a in range(len(lf[1])):
            lf[i][a]=float(lf[i][a])
     return lf
#crée une list même coeficient/catégorie 

def memevaleur(lf):
# fait en sorte d'avoir les valeurs en float (comme ça c'est clair sous quel catégorie(int,str,float,list) sons mes valeurs quand ils sortent du document)    
    def sousmemevaleur(*args):
        a=lf(*args).copy()
        #crée une list avec les notes de chaques matière sous le même coeficient 
        for i in range (len(a)):
            a[i][0]= (lf(*args)[i][0])*2
            a[i][3]=(lf(*args)[i][3])/2
        return a
    return sousmemevaleur

#pour indentifier les notes à des éléves et rendre les graph plus vraisemblable
#pourquoi random? je sais pas mais mtn c'est fait je vais pas supprimer 5 mins de travail!
def names(a,lname):   
    for i in range(1):#1 for test len(a) for full
        name = randint(0,len(lname)-1)
        #crée un fichier au nom de l'éléve
        my_mkdir('/Users/matth/Desktop/Logiciel Cool/programme-py/notes-élèves/'+str(lname[name]))
        a[i].append(lname[name])
        lname.pop(name)
    return a

#calcule la moyen de la classe par matière
def lmoyc(lm):
    lmoyenneclasse=[]
    
    for i in range(4):
        z=0
        for a in range(len(lm)):
            z= z+ lm[a][i]
            if a ==(len(lm)-1):
                lmoyenneclasse.append(int(z/len(lm)))
    return lmoyenneclasse

