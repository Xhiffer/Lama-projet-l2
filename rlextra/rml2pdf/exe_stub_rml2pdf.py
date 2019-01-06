if __name__=='__main__':
	for s in [
			'import sys',
			'from rlextra.rml2pdf import rml2pdf',
			'from reportlab import rl_config',
			'rml2pdf.main(quiet=rl_config.verbose==0,fn=sys.argv[1:])'
			]:
		exec(s)
