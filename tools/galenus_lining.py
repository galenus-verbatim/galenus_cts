"""
Part of verbapie https://github.com/galenus-verbatim/verbapie
Copyright (c) 2021 Nathalie Rousseau
MIT License https://opensource.org/licenses/mit-license.php
Code policy PEP8 https://www.python.org/dev/peps/pep-0008/
"""

import argparse
import logging
from lxml import etree
from typing import List
# import moduleName
import os
import re
import shutil
import sys
# local
import config
import verbapie

"""Specific Galenus, write normalize Gipper line number in TEI
"""


# libxml options for dom document load
xml_parser = etree.XMLParser(
    dtd_validation=False,
    no_network=True,
    ns_clean=True,
    huge_tree=True,
)

# compile xsl here, one time is enough
xslt_lining = etree.XSLT(
    etree.parse(os.path.join(os.path.dirname(__file__), 'galenus_lining.xsl'), parser=xml_parser)
)
xslt_html = etree.XSLT(
    etree.parse(os.path.join(os.path.dirname(__file__), 'cts_html.xsl'), parser=xml_parser)
)


def corpus(paths_file: str, dst_dir: str):
    """Load a file with a list of paths, and process them"""
    logging.info(dst_dir + " (destination directory)")
    os.makedirs(os.path.join(dst_dir, 'xml'), exist_ok=True)
    os.makedirs(os.path.join(dst_dir, 'html'), exist_ok=True)
    tei_list = verbapie.tei_list(paths_file)
    for tei_file in tei_list:
        lining(tei_file, dst_dir)
    nav_file = os.path.join(dst_dir, 'nav.html')
    with open(nav_file, 'w') as writer:
        writer.write('<nav>\n')
        for tei_file in tei_list:
            tei_name = os.path.splitext(os.path.basename(tei_file))[0]
            writer.write('<a href="html/' + tei_name + '.html">' + tei_name + '</a>\n')
        writer.write('</nav>\n')


def lining(tei_file: str, dst_dir: str):
    tei_name = os.path.splitext(os.path.basename(tei_file))[0]
    logging.info(tei_name + " {:.0f} kb".format(os.path.getsize(tei_file) / 1024))
    # normalize spaces
    with open(tei_file, 'r', encoding="utf-8") as f:
        xml = f.read()
    xml = re.sub(r"\s+", ' ', xml, flags=re.M)
    xml = re.sub(r"(<pb[^>]*/>)\s*(</p>) *", r"\2\1", xml, flags=re.M)
    xml = re.sub(r"(<pb[^>]*/>)\s*(</div>) *", r"\2\1", xml, flags=re.M)
    tei_dom = etree.XML(
        bytes(xml, encoding='utf-8'), 
        parser=xml_parser, 
        base_url=tei_file
    )
    # tei, normalize lining and  
    tei_dom = xslt_lining(tei_dom)
    etree.indent(tei_dom, space="  ")
    xml = etree.tostring(tei_dom, encoding=str)
    xml = re.sub(r"\s*(<lb[^>]*/>) *", r"\n\1", xml)
    xml = re.sub(r" *(<milestone[^>]*/>)\s*(<lb[^>]*/>) *", r"\n\2\1", xml)
    xml = re.sub(r"(<lb[^>]*/>)\s+(<milestone[^>]*/>)", r"\1\2", xml)
    xml = re.sub(r"(<TEI)", r"\n\1", xml)

    dst_tei = os.path.join(dst_dir, 'xml', os.path.basename(tei_file))
    with open(dst_tei, 'w', encoding="utf-8") as file:
        file.write(xml)
    # rewrite TEI, 1 time only !!!
    # with open(tei_file, 'w', encoding="utf-8") as file:
    #    file.write(xml)

    # simple html transform
    tei_dom = etree.XML(
        bytes(xml, encoding='utf-8'), 
        parser=xml_parser, 
        base_url=tei_file
    )
    try:
        tei_dom = xslt_html(tei_dom)
    except:
        pass
    for error in xslt_html.error_log:
        print(error.message + " l. " + str(error.line))
    etree.indent(tei_dom, space="")
    dst_html = os.path.join(dst_dir, 'html', tei_name + '.html')

    fin = etree.tounicode(tei_dom, method='html', pretty_print=True)
    fout = open(dst_html, 'w', encoding="utf-8")
    fout.write(fin)
    """
    with open(dst_html, 'w', encoding="utf-8") as file:
        file.write(etree.tostring(tei_dom, encoding=str))
    """

def main() -> int:
    parser = argparse.ArgumentParser(
        description='(Probably very galeno-centric) Process an XML/cts greek corpus to add line numbers : <lb n="###"/>',
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('paths_file', nargs=1, type=str,
        help="""ex: ../tests/galenus.txt
a file with a list of file/glob path of xml files to process, one per line:
../../First1KGreek/data/tlg0052/*/tlg*.xml
../../First1KGreek/data/tlg0057/*/tlg*.xml
(relative paths resolved from the file they come from)
will create a folder of same name.
"""
    )
    parser.add_argument('dst_dir', nargs=1, type=str,
        help="""Where to project modified XML/cts
    """)
    args = parser.parse_args()
    corpus(args.paths_file[0], args.dst_dir[0])


if __name__ == '__main__':
    sys.exit(main())
