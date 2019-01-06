#copyright ReportLab Europe Limited. 2000-2016
#see license.txt for license details
__version__='3.3.0'
'''Sample drawing for testing the guieditor'''
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.barcharts import HorizontalBarChart, dataSample5
from reportlab.lib import colors
class SampleH5c4(Drawing):
	"Simple bar chart with absolute spacing."

	def __init__(self,width=400,height=200,*args,**kw):
		Drawing.__init__(*(self,width,height)+args, **kw)
		bc = HorizontalBarChart()
		bc.x = 50
		bc.y = 50
		bc.height = 125
		bc.width = 300
		bc.data = dataSample5
		bc.strokeColor = colors.black

		bc.useAbsolute = 1
		bc.barWidth = 10
		bc.groupSpacing = 20
		bc.barSpacing = 10

		bc.valueAxis.valueMin = 0
		bc.valueAxis.valueMax = 60
		bc.valueAxis.valueStep = 15

		bc.categoryAxis.labels.boxAnchor = 'e'
		bc.categoryAxis.categoryNames = ['Ying', 'Yang']

		self.add(bc,name='HBC')
