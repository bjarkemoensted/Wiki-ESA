cd %~dp0
del *.raw, *.l, *.w
del *.log
del *.pyc
pscp xml_parse.py generate_indices.py matrix_builder.py moensted@paper.biocmplx.nbi.dk:/lscr_paper/moensted/