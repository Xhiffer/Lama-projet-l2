# -*- coding: utf-8 -*-
"""
Created on Mon Oct 15 14:29:32 2018
@author: etudiant
"""
# =============================================================================
# à rajouter / faire
# decorateur
# class
# graph plus préçis
# info en plus dans le pdf
# =============================================================================

import time
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

globaltime =0.00
    
def timeSpend(SousFonction):
    def sousTime(*args):
        TimeIni= time.time()
        result =SousFonction(*args)
        TimeS = time.time() -TimeIni
        global globaltime
        globaltime+=  TimeS
        return result
        
    return sousTime
        
#utilisé pour crée le dernier fichier du path (chemain pour parvenir au document)  demandé Si et seulement si il n'est pas crée   
@timeSpend
def my_mkdir(name):
    if not os.path.exists(name):
         try:
             os.mkdir(name) # changer en mkdir en mkdirs si on veux crée plus que seulment ledernier ficher du path
         except OSError as e: # m'évite d'avoir des erreurs, je sais pas comment ça fonction mais le copier coller à l'air de fonctionné
             if e.errno != errno.EEXIST:
                 raise

#utiliser pour voirs si la Library est utilisé 
def test():
    print("this library is cool")
    

    
#fonction qui rend la création de graph plus symple.
# je devrais faire une class pour le rendre plus flexible
def histo(col,arange,bins,color,x,title,label):
    
    #print(col)
    plt.hist(col, range=arange, color= color, edgecolor='white',label=label)#label nom de l'histo
    #titre en position x du graph
    plt.xlabel("notes")
    #titre en position y du graph
    plt.ylabel("n étudiants")
    #titre general dy graph
    plt.title(title)
   # plt.title('Nombre d\'étudiant en fonction des notes
   #crée une  ligne rouge verticale 
    plt.axvline(x=x, color= 'red', linestyle='--')
    


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
@timeSpend    
@memevaleur # memevaleur(allflaot(lf))
def allfloat(lf):
     for i in range(len(lf)):
        for a in range(len(lf[1])):
            lf[i][a]=float(lf[i][a])
     return lf

     
#pour indentifier les notes à des éléves et rendre les graph plus vraisemblable
#pourquoi random? je sais pas mais mtn c'est fait je vais pas supprimer 5 mins de travail!
@timeSpend
def names(a,lname):   
    for i in range(1):#1 for test len(a) for full
        name = randint(0,len(lname)-1)
        #crée un fichier au nom de l'éléve
        my_mkdir('/Users/matth/Desktop/Logiciel Cool/programme-py/notes-élèves/'+str(lname[name]))
        a[i].append(lname[name])
        lname.pop(name)
    return a

#calcule la moyen de la classe par matière
@timeSpend
def lmoyc(lm):
    lmoyenneclasse=[]
    
    for i in range(4):
        z=0
        for a in range(len(lm)):
            z= z+ lm[a][i]
            if a ==(len(lm)-1):
                lmoyenneclasse.append(int(z/len(lm)))
    return lmoyenneclasse

@timeSpend
def graph(lm):
    y=lmoyc(lm)
    for f in range(1):#1 for test lm for full
        
        #la valeur qui est mutiplier par la liste est la position où seras cette liste sur la graphe.  
        ypm= [0]*y[0]+[2]*y[1]+[4]*y[2]+[6]*y[3] # moyenne de la premi matiere/ m2/m3/m4
        yp1=[1]*int(lm[f][0]) #note n°1 de eleve
        yp2=[3]*int(lm[f][1]) #note n°2 de eleve
        yp3=[5]*int(lm[f][2]) #note n°3 de eleve
        yp4=[7]*int(lm[f][3]) #note n°4 de eleve
        plt.hist(ypm, range = (0,8),color='blue',label='moyenClasse')
        
        ###### oui c'est moche :'()
        if lm[f][0]<50:
            plt.hist(yp1, range = (0,8),color='red',label='moyen'+str(lm[f][5])) #si note <50 bare histo rouge
        else :
            plt.hist(yp1, range = (0,8),color='green') #si note >50 bare histo verte
        
        
        if lm[f][1]<50:
            plt.hist(yp2, range = (0,8),color='red',)
        else :
            plt.hist(yp2, range = (0,8),color='green')
        
        if lm[f][2]<50:
            plt.hist(yp3, range = (0,8),color='red')
        else :
            plt.hist(yp3, range = (0,8),color='green')
        
        
        if lm[f][3]<50:
            plt.hist(yp4, range = (0,8),color='red')
        else :
            plt.hist(yp4, range = (0,8),color='green')
        
        #########
        
        plt.legend(loc='upper right') #présente label en haut à droite
        plt.axhline(y=50, color='black',linestyle='--') #bare rouge horizonte note 50
        plt.axhline(y=100, color='black') #bare rouge horizonte note 100/100
        plt.xlabel('valeurs')
        plt.ylabel('moyenne de la classe')
        plt.title('moyenne de chaque contrôle en fonction des notes de '+str(lm[f][5]))
        plt.savefig('/Users/matth/Desktop/Logiciel Cool/programme-py/notes-élèves/'+str(lm[f][5])+'/1.jpg') #sauvegarde l'image dans le document de l'éléve
        plt.close('all')
###############################################################################2
    with open('données.txt', 'r') as b:
        reader = csv.reader(b)
        test= list(reader) #crée une liste depuis le document données.txt
        test.pop(0)
        test=allfloat(test)
    for i in range(1): #1 for test lm for full
        histo(np.array(test)[:,0],(0,100),12,'blue',test[i][0],'col0','eleve') #histogramme du nombre d'éleve en fonction de la note de la première série de notes  
        plt.legend(loc='upper right')
        plt.savefig('/Users/matth/Desktop/Logiciel Cool/programme-py/notes-élèves/'+str(lm[i][5])+'/2.jpg')
        plt.close('all')
        
        histo(np.array(test)[:,1],(0,100),20,'orange',test[i][1],'col1',label='eleve') #histogramme du nombre d'éleve en fonction de la note de la deuxième série de notes
        plt.legend(loc='upper right')
        plt.savefig('/Users/matth/Desktop/Logiciel Cool/programme-py/notes-élèves/'+str(lm[i][5])+'/3.jpg')
        plt.close('all')
        
        histo(np.array(test)[:,2],(0,100),20,'green',test[i][2],'col2',label='eleve') #histogramme du nombre d'éleve en fonction de la note de la troisième série de notes
        plt.legend(loc='upper right')
        plt.savefig('/Users/matth/Desktop/Logiciel Cool/programme-py/notes-élèves/'+str(lm[i][5])+'/4.jpg')
        plt.close('all')
        
        histo(np.array(test)[:,3],(0,100),12,'yellow',test[i][3],'col3',label='eleve') #histogramme du nombre d'éleve en fonction de la note de la troisième série de notes
        plt.legend(loc='upper right')
        plt.savefig('/Users/matth/Desktop/Logiciel Cool/programme-py/notes-élèves/'+str(lm[i][5])+'/5.jpg')
        plt.close('all')
    
    	### camenbert qui montre les coef de chaque matière
        labels = 'Matière1', 'Matière2', 'Matière3', 'Matière4'
        sizes = [50, 100, 100, 200]
        colors = ['yellowgreen', 'gold', 'lightskyblue', 'lightcoral']
        plt.pie(sizes, labels=labels, colors=colors,autopct='%1.1f%%', shadow=True, startangle=90)
        plt.pie(sizes, labels=labels, colors=colors,autopct='%1.1f%%', shadow=True, startangle=90)
        plt.axis('equal')
        plt.savefig('/Users/matth/Desktop/Logiciel Cool/programme-py/notes-élèves/'+str(lm[i][5])+'/6.jpg')
        plt.close('all')

#integre tout les graphes "jpg" dans un pdf pour avoir une présentation propre et rajouter des infomation sous forme de text en plus autour des graphs
@timeSpend
def gen_pdf(lm):
        
        for i in range(1): #1 for test lm for full
            path = '/Users/matth/Desktop/Logiciel Cool/programme-py/notes-élèves/'+str(lm[i][5])+'/{0}.jpg' 
            pdf = PdfFileWriter()
            for num in range(1,7):  # for each slide
                # Using ReportLab Canvas to insert image into PDF
                imgTemp = BytesIO()
                imgDoc = canvas.Canvas(imgTemp, pagesize=A3)
                # Draw image on Canvas and save PDF in buffer
                imgDoc.drawImage(path.format(num), 250, 500)
                # x, y - start position
                imgDoc.save()
                # Use PyPDF to merge the image-PDF into the template
                pdf.addPage(PdfFileReader(BytesIO(imgTemp.getvalue())).getPage(0))
            pdf.write(open('/Users/matth/Desktop/Logiciel Cool/programme-py/notes-élèves/'+str(lm[i][5])+'/output'+str(lm[i][5])+'.pdf',"wb"))
        
        
       