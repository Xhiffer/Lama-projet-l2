import os
from reportlab.platypus.flowables import Spacer
from reportlab.platypus.paragraph import Paragraph
from reportlab.platypus.xpreformatted import XPreformatted
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus.tables import Table, TableStyle
class ChargesTable:

    @staticmethod
    def getFontDir():
        fontDir = os.environ.get('RL_FONTDIR',None)
        if not fontDir:
            try:
                import kfdserver
            except ImportError:
                fontDir = None
            else:
                fontDir = os.path.join(kfdserver.__path__[0],'fonts')
        return fontDir

    def __init__(self):
        pass

    def asFlowable(self):
        self.__build()
        return self.__F

    def __para(self,text,styleNum,cls=Paragraph,**kw):
        s = self.__paraStyles[styleNum]
        if kw: s = ParagraphStyle(s.name+repr(id(text)),parent=s,**kw)
        return type(text) in (type(()),type([])) and [cls(t,style=s) for t in text] or cls(text,style=s)

    def __xpre(self,text,styleNum,cls=XPreformatted,**kw):
        return self.__para(text,styleNum,cls,**kw)

    def __makeParaStyles(self):
        psn = '_%s__paraStyles' % self.__class__.__name__
        if not hasattr(self.__class__,psn):
            from reportlab.pdfbase import pdfmetrics
            fontDir = self.getFontDir()
            if fontDir is None:
                fontName = 'Helvetica-Bold'
            else:
                face = pdfmetrics.EmbeddedType1Face(os.path.join(fontDir,'eurosbe2.afm'),os.path.join(fontDir,'eurosbe2.pfb'))
                pdfmetrics.registerTypeFace(face)
                fontName = "Eurostile-BoldExtendedTwo"
            from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
            from reportlab.lib.colors import white, PCMYKColor
            from reportlab.lib import colors
            colors.fidblue = fidblue = PCMYKColor(60,40,0,20,spotName='FidelityBlue',density=100)
            colors.fidlightblue = PCMYKColor(12.1568,8.2353,0,3.9216,spotName='FidelityLightBlue',density=100)
            S = []
            a = S.append
            normal = getSampleStyleSheet()['Normal']
            a(ParagraphStyle('ct0',normal, fontName=fontName, fontSize=12,leading=14.4, spaceAfter=6, spacebefore=6,textColor=fidblue))
            a(ParagraphStyle('ct1',normal, alignment=TA_CENTER, fontName="Helvetica-Bold", fontSize=7, textColor=white, leading=1.2*7))
            a(ParagraphStyle('ct2',normal, alignment=TA_CENTER, fontName="Helvetica", fontSize=6, leading=8))
            a(ParagraphStyle('ct3',normal, alignment=TA_JUSTIFY, fontName="Helvetica", fontSize=5.5, leading=6))
            a(ParagraphStyle('ct4',normal, fontName="Helvetica-Bold", fontSize=7, textColor=white,leading=7*1.2))
            a(ParagraphStyle('ct5',normal, alignment=TA_LEFT, fontName="Helvetica", fontSize=5, leading=5.5))
            a(ParagraphStyle('ct6',normal, alignment=TA_RIGHT, fontName="Helvetica", fontSize=5, leading=5.5))
            a(ParagraphStyle('ct7',normal, alignment=TA_CENTER, fontName="Helvetica", fontSize=5, leading=5.5))
            a(ParagraphStyle('ct8',normal, alignment=TA_JUSTIFY, fontName="Helvetica", fontSize=5.5, leading=6.0))
            a(ParagraphStyle('ct9',normal, alignment=TA_CENTER, fontName="Helvetica-Bold", fontSize=6, leading=1.2*6))
            setattr(self.__class__,psn,S)

    def __build(self):
        self.__makeParaStyles()
        from reportlab.lib.colors import fidblue, fidlightblue, white
        noStyle = TableStyle([])
        verysimple = TableStyle([
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("LEFTPADDING", (0,0), (-1,-1), 0),
            ("RIGHTPADDING", (0,0), (-1,-1), 0),
            ("TOPPADDING", (0,0), (-1,-1), 0),
            ("BOTTOMPADDING", (0,0), (-1,-1), 0),
            ])

        charges_container = TableStyle([
            ('GRID', (0,0), (-1,-1), 0.3, fidblue),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("LEFTPADDING", (0,0), (-1,-1), 0),
            ("RIGHTPADDING", (0,0), (-1,-1), 0),
            ("TOPPADDING", (0,0), (-1,-1), 0),
            ("BOTTOMPADDING", (0,0), (-1,-1), 0),
            ])

        reverseVideo = TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), fidblue),
            ("FONTNAME", (0,0), (-1,-1), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,-1), 6),
            ("LEADING", (0,0), (-1,-1), 6*1.2),
            ("TEXTCOLOR", (0,0), (-1,-1), white),
            ("ALIGN", (0,0), (-1,-1), "CENTER"),
            ("LEFTPADDING", (0,0), (-1,-1), 6),
            ("RIGHTPADDING", (0,0), (-1,-1), 6),
            ("TOPPADDING", (0,0), (-1,-1), 0),
            ("BOTTOMPADDING", (0,0), (-1,-1), 0),
            ])

        fundtable = TableStyle([
            ('OUTLINE', (0,0), (-1,-1), 0.3, fidblue),
            ("BACKGROUND", (0,0), (-1,-1), fidlightblue),
            ("BACKGROUND", (0,1), (-1,-1), white),
            ("FONTNAME", (0,0), (-1,-1), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,-1), 6),
            ("LEADING", (0,0), (-1,-1), 6*1.2),
            ("FONTNAME", (0,1), (-1,-1), "Helvetica"),
            ("ALIGN", (0,0), (-1,-1), "CENTER"),
            ("TOPPADDING", (0,0), (-1,-1), 1),
            ("LEFTPADDING", (0,0), (-1,-1), 5),
            ("BOTTOMPADDING", (0,0), (-1,-1), 2),
#('BACKGROUND', (0,0), (-1,-1), pink),
#('GRID', (0,0), (-1,-1), 1, red),
            ])

        white_border = TableStyle([
            ('OUTLINE', (0,0), (-1,-1), 0.3, fidblue),
            ("BACKGROUND", (0,0), (-1,-1), white),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("ALIGN", (0,0), (-1,-1), "CENTER"),
            ("LEFTPADDING", (0,0), (-1,-1), 6),
            ("RIGHTPADDING", (0,0), (-1,-1), 6),
            ("TOPPADDING", (0,0), (-1,-1), 3),
            ("BOTTOMPADDING", (0,0), (-1,-1), 3),
            ])
        charges_params = TableStyle([
            ('OUTLINE', (0,0), (-1,-1), 0.3, fidblue),
            ("BACKGROUND", (0,0), (-1,-1), fidlightblue),
            ("BACKGROUND", (1,0), (-1,-1), white),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("LEFTPADDING", (0,0), (-1,-1), 1),
            ("RIGHTPADDING", (0,0), (-1,-1), 3),
            ("TOPPADDING", (0,0), (-1,-1), 1),
            ("BOTTOMPADDING", (0,0), (-1,-1), 3),
            ])
        self.__F = Table([ 
[
[self.__para("""Income Funds""",0),
Table([[
[Table([
[
Table([
[self.__para("""AEGON Ethical Income Inc""",1),],
                ],
    colWidths=234, rowHeights=None,style=reverseVideo,)
            ,
        ],
[
Table([["ACD/Manager", "Depositary/Trustee"],
    self.__para(["""AEGON Fund Management UK Ltd""","""Royal Bank of Scotland, Edinburgh"""],2,leading=9)],
    colWidths=(117,117), rowHeights=None,style=fundtable,)
        ],
[
Table([
["Fund Code", "Fund Type", "Charges Levied Against", "Cat Standard?",],
["AESRI", "OEIC", "Income", "No",],
                ], colWidths=[58.5,58.5,58.5,58.5], rowHeights=None,style=fundtable)
        ,
        ],
[
Table([
["Objective",],
[self.__para("""The investment objective is to deliver a total return (income plus capital growth) to investors from investment in any sterling denominated bonds, including Eurobonds, issued by a company or organisation which meets the subfund's ethical criteria as defined by the ACD.""",3),],
                ],
    colWidths=234, rowHeights=None,style=fundtable,)
            ,
        ],
    ],
    colWidths=234, rowHeights=None,style=charges_container,),
Table([
[
Table([
[self.__para("""Maxi ISA""",4),],
                ],
    colWidths=234, rowHeights=None,style=reverseVideo,)
            ,
        ],
[
Table([
[
Table([
[
Table([
[
self.__para("""Amount Invested""",5)
                                ,
self.__para("""&pound;1,000""",6)
                                ,],
[
self.__para("""Initial Charge""",5)
                                ,
self.__para("""3.50%""",6)
                                ,],
[
self.__para("""Additional Bid-Offer Spread""",5)
                                ,
self.__para("""N/A""",6)
                                ,],
[
self.__para("""Annual Management Charge""",5)
                                ,
self.__para("""1.00%""",6)
                                ,],
[
self.__para("""Other Annual Expenses""",5)
                                ,
self.__para("""0.19%""",6)
                                ,],
[
self.__para("""Yield""",5)
                                ,
self.__para("""6.47%""",6)
                                ,],
                                ],
    colWidths=(54,25), rowHeights=None,style=charges_params,)
                            ,],
                        ],
    colWidths=88, rowHeights=None, style=noStyle)
                    ,
[Spacer(0,3),
Table([
[
self.__para("""At end of year""",7),
self.__para("""Investment to date""",7),
self.__para("""Effect of deductions to date""",7),
self.__para("""Income Reinvested to Date""",7),
self.__para("""What you might get back at 7.00%""",7),
                        ],
[
self.__para("""1""",5),
self.__para("""&pound;1,000""",6),
self.__para("""&pound;48""",6),
self.__para("""&pound;66""",6),
self.__para("""&pound;1,020""",6),
                        ],
[
self.__para("""3""",5),
self.__para("""&pound;1,000""",6),
self.__para("""&pound;83""",6),
self.__para("""&pound;210""",6),
self.__para("""&pound;1,140""",6),
                        ],
[
self.__para("""5""",5),
self.__para("""&pound;1,000""",6),
self.__para("""&pound;126""",6),
self.__para("""&pound;372""",6),
self.__para("""&pound;1,270""",6),
                        ],
[
self.__para("""10""",5),
self.__para("""&pound;1,000""",6),
self.__para("""&pound;280""",6),
self.__para("""&pound;863""",6),
self.__para("""&pound;1,680""",6),
                        ],
                        ],
    colWidths=(19,28,28,29,38), rowHeights=None,style=fundtable,)]
                    ,
                ],
                ],
    colWidths=(90,144), rowHeights=None,style=verysimple,)
            ,
        ],
[
self.__para("""
                     The last line in the table shows that over 10 years, the     effect of total charges and expenses could amount to &pound;280.     Putting this another way, this would have the effect of bringing the     illustrated investment growth rate down from     7.0%     to           5.4%          a year.
                 """,8)
            ,
        ],
    ],
    colWidths=234, rowHeights=None,style=white_border,),
Table([
[
Table([
[self.__para("""Unit Trust / OEIC / SICAV""",4),],
                ],
    colWidths=234, rowHeights=None,style=reverseVideo,)
            ,
        ],
[
Table([
[
Table([
[
Table([
[
self.__para("""Amount Invested""",5)
                                ,
self.__para("""&pound;5,000""",6)
                                ,],
[
self.__para("""Initial Charge""",5)
                                ,
self.__para("""3.50%""",6)
                                ,],
[
self.__para("""Additional Bid-Offer Spread""",5)
                                ,
self.__para("""N/A""",6)
                                ,],
[
self.__para("""Annual Management Charge""",5)
                                ,
self.__para("""1.00%""",6)
                                ,],
[
self.__para("""Other Annual Expenses""",5)
                                ,
self.__para("""0.19%""",6)
                                ,],
[
self.__para("""Yield""",5)
                                ,
self.__para("""6.47%""",6)
                                ,],
                                ],
    colWidths=(54,25), rowHeights=None,style=charges_params,)
                            ,],
                        ],
    colWidths=88, rowHeights=None, style=noStyle)
                    ,
[Spacer(0,3),
Table([
[
self.__para("""At end of year""",7),
self.__para("""Investment to date""",7),
self.__para("""Effect of deductions to date""",7),
self.__para("""Income Reinvested to Date""",7),
self.__para("""What you might get back at 6.00%""",7),
                        ],
[
self.__para("""1""",5),
self.__para("""&pound;5,000""",6),
self.__para("""&pound;240""",6),
self.__para("""&pound;329""",6),
self.__para("""&pound;5,060""",6),
                        ],
[
self.__para("""3""",5),
self.__para("""&pound;5,000""",6),
self.__para("""&pound;403""",6),
self.__para("""&pound;1,030""",6),
self.__para("""&pound;5,550""",6),
                        ],
[
self.__para("""5""",5),
self.__para("""&pound;5,000""",6),
self.__para("""&pound;600""",6),
self.__para("""&pound;1,810""",6),
self.__para("""&pound;6,090""",6),
                        ],
[
self.__para("""10""",5),
self.__para("""&pound;5,000""",6),
self.__para("""&pound;1,270""",6),
self.__para("""&pound;4,090""",6),
self.__para("""&pound;7,680""",6),
                        ],
                        ],
    colWidths=(19,28,28,29,38), rowHeights=None,style=fundtable,)]
                    ,
                ],
                ],
    colWidths=(90,144), rowHeights=None,style=verysimple,)
            ,
        ],
[
self.__para("""The last line in the table shows that over 10 years, the   effect of total charges and expenses could amount to &pound;1,270.     Putting this another way, this would have the effect of bringing the     illustrated investment growth rate down from     6.0%     to           4.4%          a year. """,8)
            ,
        ],
    ],
    colWidths=234, rowHeights=None,style=white_border,)]
,],
],
    colWidths=234, rowHeights=None,style=verysimple,),
Spacer(0,5)
]
     ,],
],
    colWidths=234, rowHeights=None,style=verysimple,)

class JumboChargesTable:

    def __init__(self):
        pass

    def asFlowable(self):
        self.__build()
        return self.__F

    def __makeParaStyles(self):
        psn = '_%s__paraStyles' % self.__class__.__name__
        if not hasattr(self.__class__,psn):
            from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
            from reportlab.lib.colors import black
            S = []
            a = S.append
            normal = getSampleStyleSheet()['Normal']
            a(ParagraphStyle(
                    name="jumbo_inside_table_header" ,
                    parent=normal,
                    firstLineIndent=0,
                    rightIndent=0,
                    leftIndent=0,
                    spaceBefore=0,
                    spaceAfter=0,
                    alignment=TA_CENTER,
                    fontName="Helvetica-Bold",
                    fontSize=4.5,
                    leading=5.5,
                    textColor=black,
                    ))
            a(ParagraphStyle(
                    name="jumbo_between_charges_tables" ,
                    parent=normal,
                    firstLineIndent=0,
                    rightIndent=5,
                    leftIndent=5,
                    spaceBefore=0,
                    spaceAfter=0,
                    alignment=TA_JUSTIFY,
                    fontName="Helvetica",
                    fontSize=5.5,
                    leading=6.6,
                    textColor=black,
                    ))

            a(ParagraphStyle(
                    name="jumbo_inside_charges_table_body" ,
                    parent=normal,
                    firstLineIndent=0,
                    rightIndent=0,
                    leftIndent=0,
                    spaceBefore=2,
                    spaceAfter=0,
                    alignment=TA_CENTER,
                    fontName="Helvetica-Bold",
                    fontSize=5.5,
                    leading=6.5,
                    textColor=black,
                    ))
            setattr(self.__class__,psn,S)

    def __para(self,text,styleNum,cls=Paragraph,**kw):
        s = self.__paraStyles[styleNum]
        if kw: s = ParagraphStyle(s.name+repr(id(text)),parent=s,**kw)
        return type(text) in (type(()),type([])) and [cls(t,style=s) for t in text] or cls(text,style=s)

    def __xpre(self,text,styleNum,cls=XPreformatted,**kw):
        return self.__para(text,styleNum,cls,**kw)

    def __build(self):
        self.__makeParaStyles()
        from reportlab.lib.colors import fidblue, fidlightblue, white, black
        #noStyle = TableStyle([])
        Jumbo_Fund_Table_Container = TableStyle([
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,0), 8),
            ("TEXTCOLOR", (0,0), (-1,0), white,),
            ("BACKGROUND", (0,0), (-1,0), fidblue),
            ("TEXTCOLOR", (0,1), (-1,-1), black),
            ("OUTLINE", (0,0),(-1,-1), 0.75, fidblue),
            ("ALIGN", (0,0), (-1,0), "CENTER"),
            ("ALIGN", (0,0), (-1,-1), "CENTER"),
            ("LEFTPADDING", (0,0),(-1,-1), 0),
            ("RIGHTPADDING", (0,0),(-1,-1), 0),
            ("BOTTOMPADDING", (0,0), (-1,0), 1),
            ("TOPPADDING", (0,0), (-1,0), 1),
            ("BOTTOMPADDING", (0,1), (-1,-1), 0),
            ("TOPPADDING", (0,1), (-1,-1), 0),
            ])

        Jumbo_Fund_Table_One = TableStyle([
            ("FONT", (0,0),(-1,-1), "Helvetica-Bold", 5, 8),
            ("GRID", (0,0),(-1,-1), 0.75, fidblue),
            ("BACKGROUND", (0,0), (-1,0), fidlightblue),
            ("LEFTPADDING", (0,0),(-1,-1), 0),
            ("RIGHTPADDING", (0,0),(-1,-1), -1),
            ("BOTTOMPADDING", (0,0),(-1,-1), 4),
            ("TOPPADDING", (0,0),(-1,-1), 2),
            ("VALIGN", (0,0), (-1,0), "MIDDLE"),
            ("VALIGN", (0,1), (-1,-1), "TOP"),
            ])

        Jumbo_Fund_Table_Two = TableStyle([
            ("FONT", (0,0), (-1,0), "Helvetica-Bold", 5, 8),
            ("FONT", (0,1), (-1,-1), "Helvetica", 5, 8),
            ("BACKGROUND", (0,0), (-1,0), fidlightblue),
            ("OUTLINE", (0,0), (0,1), 0.75, fidblue),
            ("OUTLINE", (1,0), (1,1), 0.75, fidblue),
            ("LINEBELOW", (0,0), (-1,0), 0.75, fidblue),
            ("LEFTPADDING", (0,0), (-1,-1), -1),
            ("RIGHTPADDING", (0,0), (-1,-1), -1),
            ("BOTTOMPADDING", (0,0), (-1,-1), 0),
            ("TOPPADDING", (0,0), (-1,-1), 1),
            ("ALIGN", (0,0),(-1,-1), "CENTER"),
            ])

        Jumbo_Fund_Charges_Table = TableStyle([
            ("FONT", (0,0), (-1,0), "Helvetica-Bold", 4.5, 5.5),
            ("FONT", (0,1), (-1,-1), "Helvetica-Bold", 5, 6.5),
            ("OUTLINE", (0,0), (-1,0), 0.75, fidblue),
            ("LINEBEFORE", (0,1), (0,-1), 0.75, fidblue),
            ("LINEAFTER", (-1,1), (-1,-1), 0.75,fidblue),
            ("LINEBELOW", (0,-1), (-1,-1), 0.75,fidblue),
            ("LEFTPADDING", (0,0),(-1,-1), -1),
            ("RIGHTPADDING", (0,0),(-1,-1), -1),
            ("BOTTOMPADDING", (0,0),(-1,-1), 1),
            ("TOPPADDING", (0,0),(-1,-1),1),
            ("ALIGN", (0,0),(-1,-1), "CENTER"),
            ])

        self.__F = Table(data=[
["Fid FIF Special Situations Fund",],
[
Table(data=[
[
[self.__para("""Maximum""",0),self.__para("""Initial Charges""",0), self.__para("""inside ISA/PEP""",0)],
[self.__para("""Maximum""",0),self.__para("""Initial Charges""",0),self.__para("""outside ISA/PEP""",0)],
[self.__para("""Annual""",0), self.__para("""Charges""",0)],
[self.__para("""Other""",0), self.__para("""Charges""",0)],
self.__para("""Yield""",0),
[self.__para("""Effect of""",0), self.__para("""Deductions p.a.""",0), self.__para("""inside ISA/PEP""",0)],
[self.__para("""Effect of""",0), self.__para("""Deductions p.a.""",0), self.__para("""outside ISA/PEP""",0)],
[self.__para("""Charges""",0), self.__para("""levied""",0), self.__para("""against""",0)],
                ],
[
self.__para("""3.50%""",0),
self.__para("""3.50%""",0),
self.__para("""1.50%""",0),
self.__para("""0.19%""",0),
self.__para("""0.35%""",0),
[self.__para("""From 7.00% to""",0), self.__para("""4.84% per year""",0)],
[self.__para("""From 6.00% to""",0), self.__para("""3.86% per year""",0)],
self.__para("""Income""",0),
                ],
                ],
    colWidths=[40.25,40.25,18.25,18.25,18.25,40.25,40.25,18.25], rowHeights=None,style=Jumbo_Fund_Table_One,)
            ,
        ],
[
Table(data=[
[
"ACD/Manager",
"Depositary/Trustee",
                    ],
[
"""Fidelity Investment Services Limited""",
"""J.P.Morgan Trustee and Depository Company Limited""",
                    ],
                ],
    colWidths=[117,117], rowHeights=None,style=Jumbo_Fund_Table_Two,)
            ,
        ],
[
[Spacer(0,5),
self.__para("""An example of the effect of 
    charges and expenses on an ISA/PEP investment into the fund""",1),
Spacer(0,5)]
            ,
        ],
[
Table(data=[
[
[self.__para("""At end""",0), self.__para("""of year""",0)],
[self.__para("""Investment""",0), self.__para("""to date""",0)],
[self.__para("""Effect of""",0), self.__para("""Deductions to date""",0)],
[self.__para("""What you might get""",0),self.__para("""back at 7.00%""",0)],
                ],
[
self.__para("""1""",2),
self.__para("""&pound;1,000""",2),
self.__para("""&pound;54""",2),
self.__para("""&pound;1,010""",2),
                ],
[
self.__para("""3""",2),
self.__para("""""",2),
self.__para("""&pound;100""",2),
self.__para("""&pound;1,120""",2),
                ],
[
self.__para("""5""",2),
self.__para("""""",2),
self.__para("""&pound;157""",2),
self.__para("""&pound;1,240""",2),
                ],
[
self.__para("""10""",2),
self.__para("""""",2),
self.__para("""&pound;362""",2),
self.__para("""&pound;1,600""",2),
                ],
            ],
    colWidths=[56.5,56.5,56.5,56.5], rowHeights=None,style=Jumbo_Fund_Charges_Table,)
            ,
        ],
[
[Spacer(0,1.5),
self.__para("""
    The last line in the table shows that over 10 years the effect of 
    total charges could amount to &pound;362. Putting it 
    another way, this would have the effect of bringing the illustrated 
    investment growth from 7.00% down to 
    4.84%.
    """,1),
Spacer(0,5)]
            ,
        ],
[
[Spacer(0,5),
self.__para("""An example of the effect of 
    charges and expenses on an investment directly into the fund""",1),
Spacer(0,5)]
            ,
        ],
[
Table(data=[
[
[self.__para("""At end""",0), self.__para("""of year""",0)],
[self.__para("""Investment""",0),self.__para("""to date""",0)],
[self.__para("""Effect of""",0), self.__para("""Deductions to date""",0)],
[self.__para("""What you might get""",0), self.__para("""back at 6.00%""",0)],
                ],
[
self.__para("""1""",2),
self.__para("""&pound;1,000""",2),
self.__para("""&pound;53""",2),
self.__para("""&pound;1,000""",2),
                ],
[
self.__para("""3""",2),
self.__para("""""",2),
self.__para("""&pound;97""",2),
self.__para("""&pound;1,090""",2),
                ],
[
self.__para("""5""",2),
self.__para("""""",2),
self.__para("""&pound;150""",2),
self.__para("""&pound;1,180""",2),
                ],
[
self.__para("""10""",2),
self.__para("""""",2),
self.__para("""&pound;330""",2),
self.__para("""&pound;1,460""",2),
                ],
            ],
    colWidths=[55.5,55.5,55.5,55.5], style=Jumbo_Fund_Charges_Table,)
            ,
        ],
[
[Spacer(0,1.5),
self.__para("""
    The last line in the table shows that over 10 years the effect of 
    total charges could amount to &pound;330. Putting it 
    another way, this would have the effect of bringing the illustrated 
    investment growth from 6.00% down to 
    3.86%.
    """,1),
Spacer(0,5)]
            ,
        ],
        ],
    colWidths=234, rowHeights=None,style=Jumbo_Fund_Table_Container,)
