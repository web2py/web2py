"""Convert a FAQ (AlterEgo) markdown dump into ReSt documents using pandoc

**Todo**
#. add titles
#. add logging
#. add CLI with optparse
"""


import os
import sys
import glob
import subprocess
import logging

indir = 'faq_markdown'
outdir = 'faq_rst'

inpath = os.path.join('.', indir)
outpath = os.path.join('.', outdir)

pattern = inpath + '/*.txt'
out_ext = 'rst'


for file in glob.glob(pattern):
    infile = file
    file_basename = os.path.basename(file)
    outfile_name = os.path.splitext(file_basename)[0] + '.' + out_ext
    outfile = os.path.join(outpath, outfile_name)
    # pandoc -s -w rst --toc README -o example6.text
    logging.info("converting file %s to format <%s>" % (file_basename, out_ext))
    convert_call = ["pandoc",
                         "-s",
                         "-w", out_ext,
                         infile,
                         "-o", outfile
                        ]
    p = subprocess.call(convert_call)

logging.info("Finshed!")

