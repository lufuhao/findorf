"""
HMMER tabular output parser.

This is needed because HMMER (somewhat stupidly) outputs human
readable tabular output with variable number of spaces as
delimiters. This wouldn't be a problem, but the last column definitely
contains spaces. Furthermore, is that a guarantee that domain doesn't
have a space? If it does, each numeric column could be offset by one
(silently!).

Even more ridiculous is that if one tries to make a parser based on
fixed widths, this still isn't sufficient to parse HMMER output. Why?
Because the column headers are split across two rows. This is why we
have to specify columns.
"""
import pdb
import csv
from collections import namedtuple
from BioRanges.lightweight import Range, SeqRange

DomainHit = namedtuple("DomainHit", ["target_name", "query_name",
                                     "accession", "qlen", "seq_evalue", "seq_score",
                                     "seq_bias", "domain_num", "total_domains",
                                     "domain_cevalue", "domain_ievalue",
                                     "domain_score", "domain_bias", "ali_from", "ali_to"])
def make_hmmer_parser(hmmer_file):
    """
    Return a function that parses HMMER files, based on looking at the
    third row's column widths.
    """
    col_widths_values = list()
    for i, line in enumerate(hmmer_file):
        if i == 1:
            header = line.strip()
        if i == 2:
            assert line.startswith("#-")
            # get max column width based on these delimiters
            splits = re.findall(r"[ \#]+-+", line)
            col_widths_values = map(len, splits)
            break
    pos = 0
    widths = list()
    columns = dict()
    num_columns = len(col_widths_values)
    for i, width in enumerate(col_widths_values):
        colname = HMMER_COLS[i]
        if i+1 == num_columns:
            end = None
        else:
            end = pos+width
        columns[colname] = (pos, end)
        pos += width
        
    def parser(file):
        lines = list()
        for line in file:
            if line.startswith("#"):
                continue
            row = dict()
            for field, pos in columns.iteritems():
                start, end = pos
                row[field] = line[start:end].strip()
            lines.append(row)
        return lines

    return parser

def add_pfam_domain_hits(contigs, domain_hits_file):
    """
    Parse a domain hits table (see below for reference) into
    dictionary of named tuples and SeqRange objects.
    
    ftp://selab.janelia.org/pub/software/hmmer3/3.0/Userguide.pdf,
    page 38

    Converting from amino acid (1-indexed) to 0-indexed nucleotide
    space:

    DF in +3 frame, amino acid 3, reported as position 3.

    zi_frame = zero-indexed frame

    npos = 3*(aapos) - 3 + abs(zi_frame)

                 aapos
                  |
     prot   1--2--3--4--5--6--7--8-
            |     |
     nucl |------------------------|
          0       |
                  8

    frame: 2
                      aapos
                       |
     prot  1--2--3--4--5--6--7--8-
           |           |
     nucl |------------------------|
          0            |
                       13

    frame: 1
    
         aapos
          |                    
    prot  1--2--3--4--5--6--7--8-
          |    
     nucl |------------------------|
          0    
                                
    """

    domain_hits = dict()

    # make HMMER parser
    pfam_dict = dict()
    for line in csv.DictReader(domain_hits_file, delimiter="\t"):
        key = line['query_name']

        # remove strand from contig name
        tmp = key.split("_")
        query = '_'.join(tmp[:-1])
        frame = int(tmp[-1])
        strand = "-" if frame < 0 else "+"
        
        seqlen = len(contigs[query].seq)
        dh = DomainHit(line["target_name"], query,
                       line["target_accession"], line["qlen"], line["seq_evalue"],
                       line["seq_score"], line["seq_bias"], line["domain_num"],
                       line["total_domains"], line["domain_cevalue"],
                       line["domain_ievalue"], line["domain_score"],
                       line["domain_bias"], line["ali_from"], line["ali_to"])
        data = {"domain_hit":dh, "frame":frame}
        start = (abs(frame) - 1) + 3*int(line["ali_from"]) - 3
        end = (abs(frame) - 1) + 3*int(line["ali_to"]) - 3
        assert(start <= end)
        seqrng = SeqRange(Range(start, end), seqname=query,
                          strand="+", seqlength=seqlen, data=data)
        contigs[query].add_pfam(seqrng)
        
