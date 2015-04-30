__author__ = 'Sebastian Schüpbach'
__copyright__ = 'Copyright 2015, swissbib project, UB Basel'
__license__ = 'http://opensource.org/licenses/gpl-2.0.php'
__version__ = '0.1'
__maintainer__ = 'Sebastian Schüpbach'
__email__ = 'sebastian.schuepbach@unibas.ch'
__status__ = 'development'

import elasticsearch_dsl as dsl
from pprint import pprint
import argparse


def mapping(estype, ofile):
    """
    Creates the mapping for Elasticsearch
    :param estype: Name of ES type
    :param ofile: Name of file where the mapping will be stored
    """
    m = dsl.Mapping(estype)
    # Set properties
    m.properties.dynamic = 'strict'
    # Adding mapping
    context = dsl.Object()
    namespaces = ['bibo', 'dbp', 'dc', 'dct', 'foaf', 'rdau', 'rdf', 'rdfs', 'skos']
    for token in namespaces:
        context = context.property(token, 'string', index='no')
    m = m.field('@context', context)
    m = m.field('@id', 'string', index='not_analyzed')
    m = m.field('@type', 'string', index='not_analyzed')
    m = m.field('bibo:edition', 'string', index='analyzed')
    m = m.field('bibo:isbn10', 'string', index='not_analyzed')
    m = m.field('bibo:isbn13', 'string', index='not_analyzed')
    m = m.field('bibo:issn', 'string', index='not_analyzed')
    m = m.field('dbp:originalLanguage', dsl.Object().property('@id', 'string', index='not_analyzed'))
    contrib = dsl.Nested()
    contrib = contrib.property('@id', dsl.String(index='no'))
    contrib = contrib.property('@type', dsl.String(index='no'))
    contrib = contrib.property('dbp:birthYear', dsl.String(index='not_analyzed'))
    contrib = contrib.property('dbp:deathYear', dsl.String(index='not_analyzed'))
    contrib = contrib.property('foaf:firstName', dsl.String(index='analyzed'))
    contrib = contrib.property('foaf:lastName', dsl.String(index='analyzed'))
    contrib = contrib.property('foaf:name', dsl.String(index='analyzed'))
    contrib = contrib.property('rdfs:label', dsl.String(index='analyzed'))
    contrib = contrib.property('skos:note', dsl.String(index='analyzed'))
    m = m.field('dc:contributor', contrib)
    m = m.field('dc:format', 'string', index='analyzed')
    m = m.field('dct:alternative', 'string', index='analyzed', fields={'folded': dsl.String(analyzer='text_folded')})
    m = m.field('dct:bibliographicCitation', 'string', index='analyzed', analyzer='standard')
    m = m.field('dct:hasPart', 'string', index='analyzed')
    m = m.field('dct:isPartOf', dsl.Object().property('@id', 'string', index='not_analyzed'))
    m = m.field('dct:issued', 'string', index='analyzed')
    m = m.field('dct:language', dsl.Object().property('@id', 'string', index='not_analyzed'))
    m = m.field('dct:subject', dsl.Object().property('@id', 'string', index='not_analyzed'))
    m = m.field('dct:title', 'string', index='analyzed', fields={'folded': dsl.String(analyzer='text_folded')})
    m = m.field('rdau:contentType', dsl.Object().property('@id', 'string', index='not_analyzed'))
    m = m.field('rdau:dissertationOrThesisInformation', 'string', index='analyzed')
    m = m.field('rdau:mediaType', dsl.Object().property('@id', 'string', index='not_analyzed'))
    m = m.field('rdau:modeOfIssuance', dsl.Object().property('@id', 'string', index='not_analyzed'))
    m = m.field('rdau:noteOnResource', 'string', index='not_analyzed')
    m = m.field('rdau:placeOfPublication', dsl.Object().property('@id', 'string', index='not_analyzed'))
    m = m.field('rdau:publicationStatement', 'string', index='analyzed')
    m = m.field('rdfs:isDefinedBy', dsl.Object().property('@id', 'string', index='analyzed', analyzer='extr_id'))
    # Save the mapping in ES
    of = open(ofile, mode='w')
    pprint(m.to_dict(), stream=of)
    of.close()
    # m.save(esindex, using=escon)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Creates the mapping for Elasticsearch")
    parser.add_argument('type', metavar='<name>', type=str, help='Name of ES type')
    parser.add_argument('outputfile', metavar='<file>', type=str, help='Output file')
    args = parser.parse_args()

    mapping(args.type, args.outputfile)