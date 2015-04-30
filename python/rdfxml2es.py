__author__ = 'Sebastian Schüpbach'
__copyright__ = 'Copyright 2015, swissbib project, UB Basel'
__license__ = 'http://opensource.org/licenses/gpl-2.0.php'
__version__ = '0.1'
__maintainer__ = 'Sebastian Schüpbach'
__email__ = 'sebastian.schuepbach@unibas.ch'
__status__ = 'development'

import re
from rdflib import Graph
from pyld import jsonld
from jsmin import jsmin
from json import loads
from elasticsearch import Elasticsearch
from http import client


class Rdfxml2Es:

    def __init__(self, file, ctx, frame, host, port, esindex, indctrl, extcont):
        self.file = file
        self.ctx = ctx
        self.frame = frame
        self.host = host
        self.port = port
        self.index = esindex
        self.indctrl = indctrl
        self.extcont = extcont
        try:
            h1 = client.HTTPConnection(self.host, self.port)
            h1.connect()
            h1.close()
            self.of = Elasticsearch([{'host': self.host, 'port': self.port}])
            if self.of.indices.exists(self.index):
                raise Exception('Error', 'Elasticsearch index already exists.')
        except Exception as inst:
            exit("Error: " + inst.args[1])
        else:
            if self.indctrl is not None:
                self.of.indices.create(index=self.index, body=self.loadjson(self.indctrl))
            else:
                self.of.indices.create(index=self.index)

    @staticmethod
    def loadjson(ifile):
        """
        Loads a file containing valid JSON-LD objects and removes comments
        :param ifile:
        :return Object of type Dictionary:
        """
        with open(ifile, 'r') as f:
            raw = f.read()
        jsonstr = jsmin(raw)
        return loads(jsonstr)

    @staticmethod
    def stripchars(string):
        return ''.join(re.split('\t+|\n+', string))

    def parsexml(self):
        raise NotImplementedError

    def rdf2es(self, string, bibo):
        g = Graph().parse(data=string)
        jldstr = g.serialize(format='json-ld',
                             indent=4)
        if bibo:
            esdoc = jsonld.compact(loads(jldstr.decode('utf-8')), self.loadjson(self.ctx))
            doctype = 'document'
        else:
            test = loads(jldstr.decode('utf-8'))
            esdoc = jsonld.frame(test, self.loadjson(self.frame))['@graph'][0]
            esdoc['@context'] = self.loadjson(self.ctx)
            doctype = 'bibliographicResource'
        self.of.index(index=self.index, doc_type=doctype, body=esdoc)


class OneLineXML(Rdfxml2Es):

    def parsexml(self):
        with open(self.file) as rdfxml:
            docstart = re.compile('<bibo:Document|<dct:BibliographicResource')
            xmlstart = re.compile('<?xml version')
            rdfstart = re.compile('<rdf:RDF')
            bibo = re.compile('<bibo:Document')
            header = str()
            footer = '</rdf:RDF>'
            for line in rdfxml:
                if xmlstart.search(line):
                    header = self.stripchars(line)
                elif rdfstart.search(line):
                    header += self.stripchars(line)
                elif docstart.search(line):
                    doc = header + self.stripchars(line) + footer
                    self.rdf2es(doc, bibo.search(doc))
                else:
                    continue


class MultiLineXML(Rdfxml2Es):

    def parsexml(self):
        with open(self.file) as rdfxml:
            docstart = re.compile('<bibo:Document|<dct:BibliographicResource')
            xmlstart = re.compile('<?xml version')
            rdfstart = re.compile('<rdf:RDF')
            docend = re.compile('</bibo:Document|</dct:BibliographicResource')
            bibo = re.compile('<bibo:Document')
            reclines = False
            doc = str()
            header = str()
            footer = '</rdf:RDF>'
            for line in rdfxml:
                if xmlstart.search(line):
                    header = self.stripchars(line)
                elif rdfstart.search(line):
                    header += self.stripchars(line)
                elif docstart.search(line):
                    reclines = True
                    doc = header + self.stripchars(line)
                elif docend.search(line):
                    doc += self.stripchars(line) + footer
                    self.rdf2es(doc, bibo.search(doc))
                    reclines = False
                elif reclines:
                    doc += self.stripchars(line)
                else:
                    continue


if __name__ == '__main__':
    oneLiner = True
    file = '/home/sebastian/workspace/utilities/examples/xml.rdf'
    jldctx = '/home/sebastian/workspace/utilities/examples/04/context.jsonld'
    jldframe = '/home/sebastian/workspace/utilities/examples/04/frame.jsonld'
    host = 'localhost'
    port = 9200
    esindex = 'itest37'
    indctrl = '/home/sebastian/workspace/utilities/examples/04/indctrl.json'
    extcont = False
    if oneLiner:
        obj = OneLineXML(file, jldctx, jldframe, host, port, esindex, indctrl, extcont)
    else:
        obj = MultiLineXML(file, jldctx, jldframe, host, port, esindex, indctrl, extcont)
    obj.parsexml()