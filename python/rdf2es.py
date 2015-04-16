#!/usr/bin/python3

__author__ = 'Sebastian Schüpbach'
__copyright__ = 'Copyright 2015, swissbib project, UB Basel'
__license__ = 'http://opensource.org/licenses/gpl-2.0.php'
__version__ = '1.0'
__maintainer__ = 'Sebastian Schüpbach'
__email__ = 'sebastian.schuepbach@unibas.ch'
__status__ = 'development'

"""
Parses serialized RDF triples, converts them to JSON-LD in extended document format
by providing a context file and finally either outputs the result as a file or loads it
into an Elasticsearch index.
The Script is inspired by the article on http://journal.code4lib.org/articles/7949
"""

import argparse
import re
from json import load
from subprocess import check_output
from elasticsearch import Elasticsearch
from pprint import pprint
from pyld import jsonld
from http import client
from sys import exit
from os import path


class Rdf2JsonLD:

    def __init__(self, ifile, frame, rdfformat, docs, extcont):
        self.ifile = ifile
        self.frame = frame
        self.format = rdfformat
        self.docs = docs
        self.extcont = extcont
        self.nquads = str()
        self.offsets = list()
        self.newdoc = list()

    def parserdf(self):
        print("Parsing RDF file")
        self.nquads = check_output(['rapper', '-i', self.format, '-o', 'nquads', self.ifile],
                                   universal_newlines=True)
        # As rapper returns an ASCII-encoded string, a conversion back to UTF-8 is required.
        self.nquads = self.nquads.encode('ascii')
        self.nquads = self.nquads.decode('raw_unicode_escape')

    def sequencerdf(self):
        print("Sequencing RDF file")
        # Search for subjects in nquad triples
        pattern = re.compile('^(<.*?>)', re.MULTILINE)
        subjects = pattern.findall(self.nquads)
        # Identify row numbers of new subjects
        i = 1
        self.newdoc = [0]
        for subj in subjects[0:len(subjects)-2]:
            if subj != subjects[i]:
                self.newdoc.append(i)
            i += 1
        # Get offsets of linebreaks. First token of new line begins at index offset + 1,
        # last token is at index <next offset>
        self.offsets = [-1]
        self.offsets.extend([m.start() for m in re.finditer('\n', self.nquads)])
        self.offsets.append(len(self.nquads)-1)
        # newdoc serves as an index to offsets list: newdoc[0] signifies offset=0,
        # newdoc[len(offsets)-1] means very last token of nquads.
        self.newdoc.append(len(self.offsets) - 1)
        self.newdoc.sort()

    def output(self, doc):
        pass

    def rdf2jsonld(self):
        # Extract tokens from offset + 1 to <n-th offset after> (n = args.docs)
        i = 0
        while i < len(self.newdoc) - 1:
            if i + self.docs >= len(self.newdoc) - 1:
                j = len(self.newdoc) - 1
            else:
                j = i + self.docs
            # Serializing RDF into JSON-LD by method from_rdf results in the so called
            # expanded document form, i.e. a format that doesn't contain any namespaces
            print("Serializing RDF file to JSON-LD")
            expand = jsonld.from_rdf(self.nquads[self.offsets[self.newdoc[i]] + 1:self.offsets[self.newdoc[j]]])
            i = j
            # The compacted JSON-LD document form offers the possibility to include a context
            # (i.e. namespaces) and thus reduces redundancy
            print("Converting to compacted document form")
            compacted = jsonld.compact(expand, load(open(self.frame, 'r')))
            print("Indexing documents")
            for graph in compacted["@graph"]:
                if self.extcont is True:
                    graph["@context"] = path.abspath(args.frame)
                else:
                    graph["@context"] = compacted["@context"]
                self.output(graph)


class JsonLD2ES(Rdf2JsonLD):

    def __init__(self, ifile, frame, rdfformat, docs, extcont,
                 esindex, estype, indctrl, host, port):
        Rdf2JsonLD.__init__(self, ifile, frame, rdfformat, docs, extcont)
        self.index = esindex
        self.type = estype
        self.indctrl = indctrl
        try:
            h1 = client.HTTPConnection(host, port)
            h1.connect()
            h1.close()
            self.of = Elasticsearch([{'host': host, 'port': port}])
            if self.of.indices.exists(self.index):
                raise Exception('Error', 'Elasticsearch index already exists.')
        except Exception as inst:
            exit("Error: " + inst.args[1])
        else:
            if self.indctrl is not None:
                try:
                    indctrl = load(open(self.indctrl, 'r'))
                except FileNotFoundError as inst:
                    exit("Error: " + inst.args[1])
                else:
                    self.of.indices.create(index=self.index, body=indctrl)
            else:
                self.of.indices.create(index=self.index)

    def output(self, doc):
        self.of.index(index=self.index, doc_type=self.type, body=doc)


class JsonLD2File(Rdf2JsonLD):

    def __init__(self, ifile, frame, rdfformat, docs, extcont, ofile):
        Rdf2JsonLD.__init__(self, ifile, frame, rdfformat, docs, extcont)
        try:
            self.of = open(ofile, mode='x')
        except Exception as inst:
            exit("Error: " + inst.args[1])

    def output(self, doc):
        pprint(doc, stream=self.of)

    def __del__(self):
        self.of.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Indexing RDF file in Elasticsearch")
    parser.add_argument('ifile', metavar='<filename>', type=str, help='Path to serialized RDF triples file')
    parser.add_argument('frame', metavar='<filename>', type=str, help='Path to JSON-LD frame file')
    parser.add_argument('--host', metavar='<ip>', type=str, default='localhost', help='Ip of search engine host')
    parser.add_argument('--port', metavar='<port>', type=int, default=9200, help='Port number of search engine')
    parser.add_argument('--index', metavar='<str>', dest='index', type=str, default='triples',
                        help='Name of Elasticsearch index. Defaults to \'triples\'')
    parser.add_argument('--type', metavar='<str>', dest='type', type=str, default='rdf',
                        help='Name of Elasticsearch type. Defaults to \'rdf\'')
    parser.add_argument('--format', metavar='<format>', dest='format', type=str,
                        choices=['rdfxml', 'ntriples', 'turtle', 'trig', 'rss-tag-soup', 'grddl', 'guess',
                                 'rdfa', 'json', 'nquads'], default='turtle',
                        help='''Format of RDF file. Possible values are: rdfxml', 'ntriples', 'turtle', 'trig',
                    'rss-tag-soup', 'grddl', 'rdfa', 'json', 'nquads' and 'guess'. Defaults to 'turtle'.''')
    parser.add_argument('--docs', metavar='<int>', dest='docs', type=int, default=50,
                        help='Maximum number of documents to be processed at the same time. Defaults to 20.')
    parser.add_argument('--output', metavar='<filename>', dest='output', type=str,
                        help='Outputs JSON-LD documents to file instead of indexing in Elasticsearch.')
    parser.add_argument('--extcont', metavar='<boolean>', dest='extcont', type=bool,
                        choices=['True', 'False'], default=False, help='Embed context as link. Defaults to False')
    parser.add_argument('--indctrl', metavar='<filename>', dest='indctrl', type=str,
                        help='File containing settings and mappings for Elasticsearch indexing.')
    args = parser.parse_args()

    if args.output is None:
        obj = JsonLD2ES(ifile=args.ifile,
                        frame=args.frame,
                        rdfformat=args.format,
                        docs=args.docs,
                        extcont=args.extcont,
                        esindex=args.index,
                        estype=args.type,
                        indctrl=args.indctrl,
                        host=args.host,
                        port=args.port)
    else:
        obj = JsonLD2File(ifile=args.ifile,
                          frame=args.frame,
                          rdfformat=args.format,
                          docs=args.docs,
                          extcont=args.extcont,
                          ofile=args.output)
    obj.parserdf()
    obj.sequencerdf()
    obj.rdf2jsonld()